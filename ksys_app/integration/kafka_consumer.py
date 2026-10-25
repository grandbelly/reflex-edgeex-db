"""
edgeEX → Kafka → ksys_app (TimescaleDB) 무손실 단방향 수집 Consumer 및 인메모리 브릿지 버퍼 (v1.4).

핵심 무손실 계약:
  1. `final_quality == 0` (BAD, `final_val = None`) 표본 100% 보존:
     - 전용 무손실 하이퍼테이블 `public.edgeex_vqt_raw` (PK: `(site_id, tag_id, ts)`, `raw_val/cond_val/final_val NULL` 허용)에
       모든 수신 표본(품질 0/1/2 전수)을 `ON CONFLICT (site_id, tag_id, ts) DO UPDATE`로 무손실 영속화.
     - 동시에 유효 수치 표본(`final_val IS NOT NULL`)은 동일 트랜잭션 내에서 `public.influx_hist` (`value NOT NULL`)에
       `ON CONFLICT (ts, tag_name) DO UPDATE`로 적재하여 기존 대시보드/연속집계 호환성 100% 유지.
  2. 수동 오프셋 커밋 (`enable_auto_commit=False`):
     - Kafka Consumer는 반드시 TimescaleDB 트랜잭션 적재(`flush_pending` / `persist_alarm_event`)가 성공한 뒤에만
       `await consumer.commit()`을 호출한다. DB 장애 시 오프셋을 커밋하지 않아 재전송을 보장한다.
  3. 시험 토픽 전용 구독 (`KAFKA_TOPICS`):
     - `KAFKA_TOPICS=edgeex.test.telemetry.vqt,edgeex.test.alarms.events,edgeex.test.health.status` 지정 시
       시험 토픽 3종만 구독하며, 미지정 시 기존 기본값(운영 3종 + 시험 3종)을 구독한다.
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from ksys_app.utils.logger import get_logger
from .kafka_config import (
    TOPIC_ALARMS_EVENTS,
    TOPIC_HEALTH_STATUS,
    TOPIC_TELEMETRY_VQT,
    TOPIC_TEST_ALARMS_EVENTS,
    TOPIC_TEST_HEALTH_STATUS,
    TOPIC_TEST_TELEMETRY_VQT,
    EdgeAlarmEvent,
    EdgeHealthStatus,
    EdgeTelemetryVQT,
    get_kafka_bootstrap_servers,
    get_kafka_group_id,
    get_kafka_topics,
    opc_quality_label,
)

logger = get_logger(__name__)

_TELEMETRY_TOPICS = {TOPIC_TELEMETRY_VQT, TOPIC_TEST_TELEMETRY_VQT}
_ALARM_TOPICS = {TOPIC_ALARMS_EVENTS, TOPIC_TEST_ALARMS_EVENTS}
_HEALTH_TOPICS = {TOPIC_HEALTH_STATUS, TOPIC_TEST_HEALTH_STATUS}


class EdgeMonitorBuffer:
    """상위 관제 화면(/edge-monitor) 및 Consumer 상태 공유용 경량 인메모리 링버퍼 싱글톤."""

    def __init__(self, max_series_len: int = 120, max_feed_len: int = 100, dedup_window: int = 500_000):
        self.max_series_len = max_series_len
        self.max_feed_len = max_feed_len
        self.dedup_window = dedup_window

        # 태그별 RAW / COND / FINAL 비교 시계열: tag_id -> deque of dict
        self.tag_series: Dict[str, Deque[Dict[str, Any]]] = {}
        # 태그별 최신 VQT 스냅샷
        self.latest_vqt: Dict[str, Dict[str, Any]] = {}
        # 사이트별 최신 /health 스냅샷
        self.site_health: Dict[str, Dict[str, Any]] = {}
        # 최근 Kafka 수신/적재 피드
        self.recent_feed: Deque[Dict[str, Any]] = deque(maxlen=max_feed_len)
        # 최근 알람 피드
        self.recent_alarms: Deque[Dict[str, Any]] = deque(maxlen=50)

        # (site_id, tag_id, ts_ms) 중복 흡수용 슬라이딩 윈도우
        self._seen_order: Deque[Tuple[str, str, int]] = deque()
        self._seen_keys: Set[Tuple[str, str, int]] = set()

        # 이미 DB 등록 확인된 태그 캐시
        self.registered_tags: Set[str] = set()

        # 텔레메트리 스트림에서 직접 집계하는 INTEG 클래스(0~5) 카운터
        self.integ_counters: Dict[str, int] = {
            "total_evaluated": 0,
            "NORMAL": 0,               # class 0
            "OUTLIER_SUPPRESSED": 0,   # class 1
            "MISSING_HELD": 0,         # class 2
            "STALE_ALARM": 0,          # class 3
            "HUNTING_DETECTED": 0,     # class 4
            "COLLECTION_STOPPED": 0,   # class 5
        }

        # Consumer 파이프라인 메트릭
        self.metrics: Dict[str, Any] = {
            "broker_servers": get_kafka_bootstrap_servers(),
            "consumer_group": get_kafka_group_id(),
            "subscribed_topics": list(get_kafka_topics()),
            "assigned_partitions": {},
            "enable_auto_commit": False,
            "broker_status": "STANDBY",  # CONNECTED | SIMULATING | DISCONNECTED | STANDBY
            "started_at": time.time(),
            "messages_total": 0,
            "telemetry_count": 0,
            "bad_quality_preserved": 0,
            "duplicates_absorbed": 0,
            "alarm_count": 0,
            "health_count": 0,
            "db_rows_written": 0,
            "vqt_raw_rows_written": 0,
            "commits_succeeded": 0,
            "db_errors": 0,
            "last_message_ts": None,
            "msg_per_sec": 0.0,
        }
        self._rate_window: Deque[float] = deque(maxlen=500)

    def _record_rate(self) -> None:
        now = time.time()
        self._rate_window.append(now)
        cutoff = now - 10.0
        while self._rate_window and self._rate_window[0] < cutoff:
            self._rate_window.popleft()
        self.metrics["msg_per_sec"] = round(len(self._rate_window) / 10.0, 2)
        self.metrics["last_message_ts"] = datetime.now(timezone.utc).strftime("%H:%M:%S")

    def write_status_file(self) -> None:
        """Consumer 메트릭 및 파티션 할당 현황을 JSON 파일로 기록."""
        status_path = Path(os.getenv("KAFKA_CONSUMER_STATUS_FILE", "logs/consumer_metrics.json"))
        try:
            status_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                "metrics": self.metrics,
                "integ_counters": self.integ_counters,
            }
            status_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception:
            pass

    def is_duplicate_vqt(self, key: Tuple[str, str, int]) -> bool:
        """(site_id, tag_id, ts_ms) 중복 여부 검사 및 등록."""
        if key in self._seen_keys:
            self.metrics["duplicates_absorbed"] += 1
            return True
        self._seen_keys.add(key)
        self._seen_order.append(key)
        if len(self._seen_order) > self.dedup_window:
            oldest = self._seen_order.popleft()
            self._seen_keys.discard(oldest)
        return False

    def ingest_telemetry(self, item: EdgeTelemetryVQT) -> bool:
        """단일 VQT 메시지를 링버퍼에 반영. 신규 키이면 True, 재전송 중복이면 False 반환."""
        if self.is_duplicate_vqt(item.dedup_key):
            return False

        self.metrics["messages_total"] += 1
        self.metrics["telemetry_count"] += 1
        if item.final_quality == 0:
            self.metrics["bad_quality_preserved"] += 1
        self._record_rate()

        self.integ_counters["total_evaluated"] += 1
        if item.integ_status in self.integ_counters:
            self.integ_counters[item.integ_status] += 1

        ts_str = item.timestamp.astimezone().strftime("%H:%M:%S")
        point = {
            "time": ts_str,
            "ts_ms": item.ts_ms,
            "tag_id": item.tag_id,
            "site_id": item.site_id,
            "channel": item.channel,
            "raw_val": item.raw_val,
            "cond_val": item.cond_val,
            "final_val": item.final_val,
            "diff_abs": item.diff_abs,
            "quality": item.final_quality,
            "final_quality": item.final_quality,
            "quality_label": opc_quality_label(item.final_quality),
            "influx_quality": item.influx_quality,
            "is_imputed": item.is_imputed,
            "integ_class": item.integ_class,
            "integ_status": item.integ_status,
            "reasons": list(item.reasons),
            "alarm_event": item.alarm_event,
            "eval_desc": item.eval_desc,
            "unit": item.unit,
        }

        if item.tag_id not in self.tag_series:
            self.tag_series[item.tag_id] = deque(maxlen=self.max_series_len)
        self.tag_series[item.tag_id].append(point)
        self.latest_vqt[item.tag_id] = point

        reasons_str = ",".join(item.reasons) if item.reasons else "NONE"
        self.recent_feed.appendleft({
            "time": ts_str,
            "topic": TOPIC_TELEMETRY_VQT,
            "site_id": item.site_id,
            "tag_id": item.tag_id,
            "channel": item.channel,
            "raw_val": f"{item.raw_val:.2f}" if item.raw_val is not None else "NULL",
            "cond_val": f"{item.cond_val:.2f}" if item.cond_val is not None else "NULL",
            "final_val": f"{item.final_val:.2f}" if item.final_val is not None else "NULL",
            "quality_label": opc_quality_label(item.final_quality),
            "influx_quality": item.influx_quality,
            "integ_class": item.integ_class,
            "integ_status": item.integ_status,
            "reasons": reasons_str,
            "summary": item.eval_desc or f"FINAL={item.final_val} (class={item.integ_class}:{item.integ_status}, reasons={reasons_str})",
        })
        return True

    def ingest_alarm(self, alarm: EdgeAlarmEvent) -> None:
        """단일 알람 이벤트를 링버퍼에 반영."""
        self.metrics["messages_total"] += 1
        self.metrics["alarm_count"] += 1
        self._record_rate()

        ts_str = alarm.triggered_at.astimezone().strftime("%H:%M:%S")
        rec = {
            "event_id": alarm.event_id,
            "time": ts_str,
            "site_id": alarm.site_id,
            "tag_id": alarm.tag_id,
            "level": alarm.level,
            "message": alarm.message,
            "value": round(alarm.value, 2),
            "unit": alarm.unit,
            "cause": alarm.cause,
            "resolved": alarm.resolved,
        }
        self.recent_alarms.appendleft(rec)
        self.recent_feed.appendleft({
            "time": ts_str,
            "topic": TOPIC_ALARMS_EVENTS,
            "site_id": alarm.site_id,
            "tag_id": alarm.tag_id,
            "channel": "alarm",
            "raw_val": f"{alarm.value:.2f}",
            "cond_val": f"L{alarm.level}",
            "final_val": f"{alarm.value:.2f}",
            "quality_label": "ALARM",
            "influx_quality": 0,
            "integ_class": 0,
            "integ_status": "ALARM_EVENT",
            "reasons": alarm.cause,
            "summary": alarm.message,
        })

    def ingest_health(self, health: EdgeHealthStatus) -> None:
        """엣지 사이트 /health 스냅샷을 링버퍼에 반영."""
        self.metrics["messages_total"] += 1
        self.metrics["health_count"] += 1
        self._record_rate()

        ts_str = datetime.fromtimestamp(health.ts_ms / 1000.0, tz=timezone.utc).astimezone().strftime("%H:%M:%S")
        self.site_health[health.site_id] = {
            "site_id": health.site_id,
            "updated_at": ts_str,
            "status": health.status,
            "pid": health.pid,
            "liveness": health.liveness,
            "mem": health.mem,
            "uptime_s": health.uptime_s,
            "stats": health.stats,
            "channels": health.channels,
            "ntp": health.ntp,
            "config_sha256": health.config_sha256,
            "tsdb_written": health.tsdb_written,
            "tsdb_buffered": health.tsdb_buffered,
            "tsdb_lost": health.tsdb_lost,
            "p1_count": health.p1_count,
            "p2_count": health.p2_count,
            "p3_count": health.p3_count,
            "unacked_count": health.unacked_count,
            "integ_stats": health.integ_stats,
        }


_EDGE_BUFFER_SINGLETON: Optional[EdgeMonitorBuffer] = None


def get_edge_monitor_buffer() -> EdgeMonitorBuffer:
    """전역 EdgeMonitorBuffer 싱글톤 반환."""
    global _EDGE_BUFFER_SINGLETON
    if _EDGE_BUFFER_SINGLETON is None:
        _EDGE_BUFFER_SINGLETON = EdgeMonitorBuffer()
    return _EDGE_BUFFER_SINGLETON


# ---------------------------------------------------------------------------
# 무손실 DB 적재 로직 (edgeex_vqt_raw 전수 보존 + influx_hist 수치 동기화)
# ---------------------------------------------------------------------------
async def persist_telemetry_batch(
    items: List[EdgeTelemetryVQT],
    buffer: Optional[EdgeMonitorBuffer] = None,
) -> Tuple[bool, int]:
    """수신된 VQT 배치를 단일 트랜잭션으로 영속화한다.
    1. `public.edgeex_vqt_raw`: `final_quality=0` (`final_val=NULL`) 표본을 포함한 **전수(100%) 표본**을
       `(site_id, tag_id, ts)` 키로 무손실 Upsert.
    2. `public.influx_hist`: 수치 표본(`final_val IS NOT NULL`)을 `(ts, tag_name)` 키로 Upsert.
    반환값: `(db_commit_ok: bool, rows_written: int)`
    """
    if not items:
        return True, 0

    buf = buffer or get_edge_monitor_buffer()
    try:
        from ksys_app.db import get_pool
        pool = await get_pool()
    except Exception as e:
        buf.metrics["db_errors"] += 1
        logger.warning(f"DB pool unavailable during Kafka telemetry persist: {e}")
        return False, 0

    new_tags: Dict[str, EdgeTelemetryVQT] = {}
    for item in items:
        if item.tag_id not in buf.registered_tags:
            new_tags[item.tag_id] = item

    # 1) edgeex_vqt_raw 무손실 전수 행 (site_id, tag_id, ts 기준 배치 내 중복 병합)
    dedup_raw: Dict[Tuple[str, str, datetime], Tuple[Any, ...]] = {}
    # 2) influx_hist 수치 행 (ts, tag_name 기준 배치 내 중복 병합)
    dedup_hist: Dict[Tuple[datetime, str], Tuple[datetime, str, float, int]] = {}

    for item in items:
        ts_dt = item.timestamp
        dedup_raw[(item.site_id, item.tag_id, ts_dt)] = (
            ts_dt,
            item.site_id,
            item.tag_id,
            item.channel,
            item.raw_val,
            item.cond_val,
            item.final_val,
            int(item.final_quality),
            int(item.influx_quality),
            int(item.integ_class),
            item.integ_status,
            json.dumps(item.reasons, ensure_ascii=False),
            item.unit,
        )
        val = item.influx_value
        if val is not None:
            dedup_hist[(ts_dt, item.tag_id)] = (
                ts_dt,
                item.tag_id,
                val,
                item.influx_quality,
            )

    raw_rows = list(dedup_raw.values())
    hist_rows = list(dedup_hist.values())

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                if new_tags:
                    tag_records = []
                    viewer_records = []
                    for idx, (tag_name, sample) in enumerate(new_tags.items(), start=1):
                        meta_json = json.dumps(
                            {
                                "source": "edgeEX",
                                "site_id": sample.site_id,
                                "channel": sample.channel,
                                "unit": sample.unit,
                            },
                            ensure_ascii=False,
                        )
                        tag_records.append((tag_name, tag_name, tag_name, sample.tag_type, meta_json))
                        viewer_records.append((tag_name, 1000 + idx * 10))

                    await conn.executemany(
                        """
                        INSERT INTO public.influx_tag (key, tag_id, tag_name, tag_type)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT DO NOTHING
                        """,
                        [(r[0], r[1], r[2], r[3]) for r in tag_records],
                    )
                    await conn.executemany(
                        """
                        INSERT INTO public.viewer_tag (tag_name, display_order, show_dashboard, show_alarm, show_trend, show_model)
                        VALUES ($1, $2, true, true, true, true)
                        ON CONFLICT (tag_name) DO NOTHING
                        """,
                        viewer_records,
                    )
                    buf.registered_tags.update(new_tags.keys())

                # 무손실 원본/INTEG 테이블 적재 (final_quality=0, final_val=NULL 포함 100% 보존)
                if raw_rows:
                    await conn.executemany(
                        """
                        INSERT INTO public.edgeex_vqt_raw (
                            ts, site_id, tag_id, channel,
                            raw_val, cond_val, final_val,
                            final_quality, influx_quality,
                            integ_class, integ_status, reasons, unit, ingested_at
                        )
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13,NOW())
                        ON CONFLICT (site_id, tag_id, ts) DO UPDATE
                        SET raw_val = EXCLUDED.raw_val,
                            cond_val = EXCLUDED.cond_val,
                            final_val = EXCLUDED.final_val,
                            final_quality = EXCLUDED.final_quality,
                            influx_quality = EXCLUDED.influx_quality,
                            integ_class = EXCLUDED.integ_class,
                            integ_status = EXCLUDED.integ_status,
                            reasons = EXCLUDED.reasons,
                            ingested_at = NOW()
                        """,
                        raw_rows,
                    )
                    buf.metrics["vqt_raw_rows_written"] += len(raw_rows)

                # 기존 influx_hist 적재 (수치 존재 표본)
                if hist_rows:
                    await conn.executemany(
                        """
                        INSERT INTO public.influx_hist (ts, tag_name, value, quality)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (ts, tag_name) DO UPDATE
                        SET value = EXCLUDED.value, quality = EXCLUDED.quality
                        """,
                        hist_rows,
                    )
                    buf.metrics["db_rows_written"] += len(hist_rows)

            return True, len(raw_rows)
    except Exception as e:
        buf.metrics["db_errors"] += 1
        logger.error(f"Failed to persist telemetry batch: {e}")
        return False, 0


async def persist_alarm_event(
    alarm: EdgeAlarmEvent,
    buffer: Optional[EdgeMonitorBuffer] = None,
) -> bool:
    """수신된 edgeEX core/alarms.py 경보 사건을 기존 alarm_history 테이블에 멱등 적재."""
    buf = buffer or get_edge_monitor_buffer()
    try:
        from ksys_app.db import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            sensor_data_str = json.dumps(alarm.to_sensor_data_json(), ensure_ascii=False)
            await conn.execute(
                """
                INSERT INTO public.alarm_history (
                    event_id, scenario_id, level, triggered_at, message,
                    sensor_data, actions_taken, acknowledged, resolved, ai_generated
                )
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, ARRAY['kafka_ingested']::text[], $7, $8, false)
                ON CONFLICT (event_id, triggered_at) DO UPDATE
                SET level = EXCLUDED.level,
                    message = EXCLUDED.message,
                    acknowledged = EXCLUDED.acknowledged,
                    resolved = EXCLUDED.resolved
                """,
                alarm.event_id,
                alarm.scenario_id,
                alarm.level,
                alarm.triggered_at,
                alarm.message,
                sensor_data_str,
                alarm.acknowledged,
                alarm.resolved,
            )
            buf.metrics["db_rows_written"] += 1
            return True
    except Exception as e:
        buf.metrics["db_errors"] += 1
        logger.warning(f"Failed to persist EdgeAlarmEvent ({alarm.event_id}): {e}")
        return False


# ---------------------------------------------------------------------------
# 비동기 Kafka Consumer 워커 (enable_auto_commit=False, DB 커밋 성공 후 오프셋 커밋)
# ---------------------------------------------------------------------------
class EdgeKafkaConsumerWorker:
    """edgeEX 토픽을 구독하여 DB 트랜잭션 성공 후에만 오프셋을 커밋하는 무손실 비동기 워커."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        group_id: Optional[str] = None,
        topics: Optional[Tuple[str, ...]] = None,
        flush_interval_s: float = 0.5,
        batch_size: int = 500,
    ):
        self.bootstrap_servers = bootstrap_servers or get_kafka_bootstrap_servers()
        self.group_id = group_id or get_kafka_group_id()
        self.topics = topics or get_kafka_topics()
        self.flush_interval_s = flush_interval_s
        self.batch_size = batch_size
        self.buffer = get_edge_monitor_buffer()
        self._stop_event = asyncio.Event()
        self._pending_vqt: List[EdgeTelemetryVQT] = []
        self._task: Optional[asyncio.Task] = None

    async def handle_raw_message(self, topic: str, payload: Dict[str, Any], persist_db: bool = True) -> bool:
        """토픽별 JSON dict 페이로드 처리.
        - `final_quality == 0` (`final_val = None`) 표본도 `_pending_vqt`에 빠짐없이 추가하여 `edgeex_vqt_raw`에 무손실 적재.
        - 재전송/과거 백필 표본도 DB `ON CONFLICT DO UPDATE`가 최종 멱등 보장하도록 `_pending_vqt`에 전달.
        """
        if topic in _TELEMETRY_TOPICS or topic.endswith(".telemetry.vqt"):
            vqt = EdgeTelemetryVQT.from_dict(payload)
            self.buffer.ingest_telemetry(vqt)
            if persist_db:
                self._pending_vqt.append(vqt)
                if len(self._pending_vqt) >= self.batch_size:
                    ok, _ = await self.flush_pending()
                    return ok
            return True
        elif topic in _ALARM_TOPICS or topic.endswith(".alarms.events"):
            alarm = EdgeAlarmEvent.from_dict(payload)
            self.buffer.ingest_alarm(alarm)
            if persist_db:
                return await persist_alarm_event(alarm, self.buffer)
            return True
        elif topic in _HEALTH_TOPICS or topic.endswith(".health.status"):
            health = EdgeHealthStatus.from_dict(payload)
            self.buffer.ingest_health(health)
            return True
        return True

    async def flush_pending(self) -> Tuple[bool, int]:
        """대기 중인 VQT 배치를 DB에 플러시. 실패 시 버퍼를 보존하고 `(False, 0)` 반환."""
        if not self._pending_vqt:
            return True, 0
        batch = self._pending_vqt[:]
        ok, count = await persist_telemetry_batch(batch, self.buffer)
        if ok:
            self._pending_vqt.clear()
        return ok, count

    async def run_forever(self) -> None:
        """aiokafka Consumer 메인 루프 (`enable_auto_commit=False`, DB 적재 성공 후에만 `consumer.commit()`)."""
        try:
            from aiokafka import AIOKafkaConsumer, ConsumerRebalanceListener
        except ImportError:
            logger.warning("aiokafka 패키지가 설치되지 않아 Kafka Consumer 워커를 대기 모드로 유지합니다.")
            self.buffer.metrics["broker_status"] = "AIOKAFKA_NOT_INSTALLED"
            return

        worker_ref = self

        class _RebalanceLogger(ConsumerRebalanceListener):
            async def on_partitions_revoked(self, revoked: Any) -> None:
                rev_list = sorted(f"{tp.topic}:{tp.partition}" for tp in revoked)
                logger.info(f"[KafkaConsumer] Partitions revoked: {rev_list}")

            async def on_partitions_assigned(self, assigned: Any) -> None:
                by_topic: Dict[str, List[int]] = {}
                for tp in assigned:
                    by_topic.setdefault(tp.topic, []).append(tp.partition)
                for t in by_topic:
                    by_topic[t].sort()
                counts = {t: len(parts) for t, parts in sorted(by_topic.items())}
                worker_ref.buffer.metrics["assigned_partitions"] = by_topic
                worker_ref.buffer.write_status_file()
                logger.info(
                    f"[KafkaConsumer] Group joined & partitions assigned (group={worker_ref.group_id}): "
                    f"counts={counts} detail={by_topic}"
                )

        backoff = 3.0
        while not self._stop_event.is_set():
            consumer = AIOKafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            )
            consumer.subscribe(topics=list(self.topics), listener=_RebalanceLogger())
            try:
                await consumer.start()
                self.buffer.metrics["broker_status"] = "CONNECTED"
                self.buffer.metrics["broker_servers"] = self.bootstrap_servers
                self.buffer.metrics["consumer_group"] = self.group_id
                self.buffer.metrics["subscribed_topics"] = list(self.topics)
                self.buffer.metrics["enable_auto_commit"] = False
                self.buffer.write_status_file()
                logger.info(
                    f"[KafkaConsumer] Connected to {self.bootstrap_servers} "
                    f"(group={self.group_id}, enable_auto_commit=False, topics={self.topics})"
                )
                backoff = 3.0

                while not self._stop_event.is_set():
                    result = await consumer.getmany(timeout_ms=500, max_records=self.batch_size)
                    if not result:
                        continue

                    batch_ok = True
                    for tp, messages in result.items():
                        for msg in messages:
                            if isinstance(msg.value, dict):
                                ok = await self.handle_raw_message(tp.topic, msg.value, persist_db=True)
                                if not ok:
                                    batch_ok = False

                    flush_ok, _ = await self.flush_pending()
                    if batch_ok and flush_ok:
                        await consumer.commit()
                        self.buffer.metrics["commits_succeeded"] += 1
                        self.buffer.write_status_file()
                        m = self.buffer.metrics
                        logger.info(
                            f"[KafkaConsumer] Batch committed: commits={m['commits_succeeded']} "
                            f"telemetry={m['telemetry_count']} vqt_raw_written={m['vqt_raw_rows_written']} "
                            f"bad_quality_preserved={m['bad_quality_preserved']} "
                            f"duplicates_absorbed={m['duplicates_absorbed']} "
                            f"alarms={m['alarm_count']} health={m['health_count']}"
                        )
                    else:
                        raise RuntimeError("DB persistence failed for polled batch; skipping offset commit to trigger redelivery")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.buffer.metrics["broker_status"] = "DISCONNECTED"
                self.buffer.write_status_file()
                logger.warning(f"[KafkaConsumer] Error or DB backpressure ({e}); retrying in {backoff:.0f}s")
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=backoff)
                except asyncio.TimeoutError:
                    pass
                backoff = min(backoff * 1.5, 30.0)
            finally:
                try:
                    await consumer.stop()
                except Exception:
                    pass
                m = self.buffer.metrics
                logger.info(
                    f"[KafkaConsumer] Stopped: commits={m['commits_succeeded']} "
                    f"telemetry={m['telemetry_count']} vqt_raw_written={m['vqt_raw_rows_written']} "
                    f"bad_quality_preserved={m['bad_quality_preserved']} "
                    f"duplicates_absorbed={m['duplicates_absorbed']} "
                    f"alarms={m['alarm_count']} health={m['health_count']}"
                )
                self.buffer.write_status_file()

    def start_background(self) -> Optional[asyncio.Task]:
        """현재 이벤트 루프에 백그라운드 태스크로 기동."""
        if self._task is not None and not self._task.done():
            return self._task
        self._stop_event.clear()
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self.run_forever(), name="edgeex-kafka-consumer")
        return self._task

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


_CONSUMER_WORKER_SINGLETON: Optional[EdgeKafkaConsumerWorker] = None


def get_kafka_consumer_worker() -> EdgeKafkaConsumerWorker:
    """전역 EdgeKafkaConsumerWorker 싱글톤 반환."""
    global _CONSUMER_WORKER_SINGLETON
    if _CONSUMER_WORKER_SINGLETON is None:
        _CONSUMER_WORKER_SINGLETON = EdgeKafkaConsumerWorker()
    return _CONSUMER_WORKER_SINGLETON


if __name__ == "__main__":
    async def _main() -> None:
        worker = get_kafka_consumer_worker()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))
            except NotImplementedError:
                # Windows SelectorEventLoop fallback
                signal.signal(sig, lambda *_: worker._stop_event.set())
        try:
            await worker.run_forever()
        finally:
            try:
                from ksys_app.db import close_pool
                await close_pool()
            except Exception:
                pass

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass
