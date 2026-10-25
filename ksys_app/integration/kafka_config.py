"""
edgeEX ↔ ksys_app Kafka 인터페이스 설정 및 메시지 스키마/변환 규격 (v1.4 — CR-EXAT-277 엣지 통합 규격 반영).

단방향 수집 토픽 3종 (Redis `stream:vqt` Sidecar Connector + `/health` 폴러 → Kafka → ksys_app):
  1. edgeex.telemetry.vqt  : 3-Tier VQT (RAW / COND / INTEG 최종값) 실시간 텔레메트리
  2. edgeex.alarms.events  : core/alarms.py ISA-18.2 공정 경보 및 체계 경보 사건
  3. edgeex.health.status  : GET /health 5초 주기 스냅샷

핵심 합의 규칙:
  - (1) integ_status & integ_class (0~5):
      0 = NORMAL
      1 = OUTLIER_SUPPRESSED
      2 = MISSING_HELD
      3 = STALE_ALARM
      4 = HUNTING_DETECTED
      5 = COLLECTION_STOPPED
  - (2) 오너 결정 "Kafka 최종값 = INTEG" (`final_val`, `final_quality`, `integ_class`, `reasons`):
      · 판정 정본은 커넥터(`upper_kafka/contract.py`)가 메시지에 실어 보낸 `final_val` 및 `reasons`이다.
      · final_quality == 0 (BAD) -> final_val = None (NULL)
      · 직전값 유지(LOCF_HELD) 또는 이상치 대체(OUTLIER_REPLACED) -> final_val = cond_val
      · 그 밖(NORMAL, HUNTING_DETECTED 등) -> final_val = raw_val
  - (3) 사유 비트 표 (`REASON_LABELS`, `REASON_BIT_NAMES`):
      · `edgeEX/src/platform/edge_platform/core/conditioning.py` (0x0001 ~ 0x20000, 18비트)와 100% 동일.
  - (4) 구독 토픽 제어 (`KAFKA_TOPICS`):
      · `KAFKA_TOPICS` 환경변수가 지정되면 해당 토픽 목록(쉼표 구분)만 구독한다.
      · 미지정 시 기존 기본값(운영 토픽 3개 + 시험 토픽 3개)을 유지한다.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)


def load_env_file_if_present(env_path: Optional[Path] = None) -> None:
    """표준 라이브러리만으로 동작하는 경량 .env 로더.
    이미 설정된 환경변수(os.environ)는 덮어쓰지 않는다(setdefault).
    """
    candidates: List[Path] = []
    custom_env = os.environ.get("EDGE_CONSUMER_ENV_FILE", "").strip()
    if custom_env:
        candidates.append(Path(custom_env))
    if env_path is not None:
        candidates.append(env_path)
    candidates.append(Path.cwd() / ".env")
    candidates.append(Path(__file__).resolve().parent.parent.parent / ".env")

    for path in candidates:
        if path.is_file():
            try:
                for raw_line in path.read_text(encoding="utf-8").splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key:
                        os.environ.setdefault(key, val)
            except Exception:
                pass
            break


load_env_file_if_present()


# ---------------------------------------------------------------------------
# Kafka 환경변수 및 토픽 상수 (운영 토픽 + 통합 시험용 edgeex.test.* 토픽)
# ---------------------------------------------------------------------------
TOPIC_TELEMETRY_VQT = os.getenv("KAFKA_TOPIC_TELEMETRY", "edgeex.telemetry.vqt")
TOPIC_ALARMS_EVENTS = os.getenv("KAFKA_TOPIC_ALARMS", "edgeex.alarms.events")
TOPIC_HEALTH_STATUS = os.getenv("KAFKA_TOPIC_HEALTH", "edgeex.health.status")

TOPIC_TEST_TELEMETRY_VQT = "edgeex.test.telemetry.vqt"
TOPIC_TEST_ALARMS_EVENTS = "edgeex.test.alarms.events"
TOPIC_TEST_HEALTH_STATUS = "edgeex.test.health.status"

ALL_EDGEEX_TOPICS: Tuple[str, ...] = (
    TOPIC_TELEMETRY_VQT,
    TOPIC_ALARMS_EVENTS,
    TOPIC_HEALTH_STATUS,
)

ALL_EDGEEX_TEST_TOPICS: Tuple[str, ...] = (
    TOPIC_TEST_TELEMETRY_VQT,
    TOPIC_TEST_ALARMS_EVENTS,
    TOPIC_TEST_HEALTH_STATUS,
)


def get_kafka_bootstrap_servers() -> str:
    """Kafka 브로커 부트스트랩 서버 주소 반환 (환경변수 우선)."""
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")


def get_kafka_group_id() -> str:
    """상위 모니터링 Consumer Group ID 반환."""
    return os.getenv("KAFKA_CONSUMER_GROUP", "ksys-upper-monitor-v1")


def get_kafka_topics() -> Tuple[str, ...]:
    """구독할 Kafka 토픽 목록 반환 (§2-E).
    - KAFKA_TOPICS 환경변수가 설정된 경우: 쉼표(,)로 구분된 토픽들만 구독
      (예: KAFKA_TOPICS=edgeex.test.telemetry.vqt,edgeex.test.alarms.events,edgeex.test.health.status)
    - 설정되지 않은 경우: 기존 기본값(운영 토픽 3종 + 시험 토픽 3종) 반환
    """
    raw = os.getenv("KAFKA_TOPICS", "").strip()
    if raw:
        parsed = tuple(t.strip() for t in raw.split(",") if t.strip())
        if parsed:
            return parsed
    return ALL_EDGEEX_TOPICS + ALL_EDGEEX_TEST_TOPICS


def is_kafka_enabled() -> bool:
    """인앱/백그라운드 Kafka Consumer 활성화 여부."""
    return os.getenv("KAFKA_ENABLED", "true").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# INTEG 상태 (0~5) 및 사유 비트마스크 매핑 (edgeEX core/conditioning.py 정본과 100% 일치)
# ---------------------------------------------------------------------------
INTEG_CLASS_TO_STATUS: Dict[int, str] = {
    0: "NORMAL",
    1: "OUTLIER_SUPPRESSED",
    2: "MISSING_HELD",
    3: "STALE_ALARM",
    4: "HUNTING_DETECTED",
    5: "COLLECTION_STOPPED",
}
INTEG_STATUS_TO_CLASS: Dict[str, int] = {v: k for k, v in INTEG_CLASS_TO_STATUS.items()}

# edgeEX/src/platform/edge_platform/core/conditioning.py REASON_LABELS (bit 0 .. bit 17)
REASON_LABELS: Tuple[Tuple[str, str], ...] = (
    ("SOURCE_BAD", "원본 품질 이상"),           # 1 << 0  (0x00001)
    ("RANGE_INVALID", "유효 범위 초과"),        # 1 << 1  (0x00002)
    ("MEDIAN_APPLIED", "미디언 적용"),          # 1 << 2  (0x00004)
    ("EWMA_APPLIED", "평활 적용"),              # 1 << 3  (0x00008)
    ("OUTLIER_REPLACED", "이상치 대체"),        # 1 << 4  (0x00010)
    ("LOCF_HELD", "직전값 유지"),               # 1 << 5  (0x00020)
    ("INTERP_BACKFILLED", "사후 보간"),         # 1 << 6  (0x00040)
    ("STALE_EXPIRED", "신선도 만료"),           # 1 << 7  (0x00080)
    ("WARMUP", "초기 상태 충전"),               # 1 << 8  (0x00100)
    ("STATE_RESET", "상태 초기화"),             # 1 << 9  (0x00200)
    ("LATE_ARRIVAL", "늦은 도착"),              # 1 << 10 (0x00400)
    ("TIME_INVALID", "시각 이상"),              # 1 << 11 (0x00800)
    ("RANGE_UNRESOLVED", "유효 범위 미정"),     # 1 << 12 (0x01000)
    ("NON_NUMERIC", "비수치"),                  # 1 << 13 (0x02000)
    ("COND_ERROR", "조건화 오류"),              # 1 << 14 (0x04000)
    ("FLATLINE", "값 고착"),                    # 1 << 15 (0x08000)
    ("HUNTING", "헌팅"),                        # 1 << 16 (0x10000)
    ("COLLECTION_STOPPED", "수집 중단"),        # 1 << 17 (0x20000)
)

REASON_BIT_NAMES: Dict[int, str] = {
    (1 << bit): name for bit, (name, _) in enumerate(REASON_LABELS)
}


def decode_reason_mask(reason_mask: int) -> List[str]:
    """정수 reason_mask 비트열을 비트 순서(0..17)의 사유 이름 목록(list[str])으로 변환.
    upper_kafka/contract.py 의 `[name for bit, (name, _) in enumerate(REASON_LABELS) if mask & (1 << bit)]`와 동일.
    """
    return [name for bit, (name, _) in enumerate(REASON_LABELS) if reason_mask & (1 << bit)]


# ---------------------------------------------------------------------------
# Quality 코드 상호 변환 (edgeEX OPC ↔ ksys_app influx_hist)
# ---------------------------------------------------------------------------
OPC_QUALITY_BAD = 0
OPC_QUALITY_UNCERTAIN = 1
OPC_QUALITY_GOOD = 2

INFLUX_QUALITY_GOOD = 0       # 정상 (queries/realtime.py WHERE quality = 0)
INFLUX_QUALITY_UNCERTAIN = 1  # 불확실 (HUNTING_DETECTED, LOCF 등)
INFLUX_QUALITY_BAD = 2        # 불량 (STALE_ALARM, COLLECTION_STOPPED, RANGE_INVALID 등)


def opc_quality_to_influx(opc_quality: Optional[int]) -> int:
    """edgeEX OPC quality(2=GOOD, 1=UNCERTAIN, 0=BAD)를
    ksys_app influx_hist.quality(0=정상, 1=불확실, 2=불량)로 변환한다.
    """
    if opc_quality is None:
        return INFLUX_QUALITY_BAD
    q = int(opc_quality)
    if q == OPC_QUALITY_GOOD:
        return INFLUX_QUALITY_GOOD
    if q == OPC_QUALITY_UNCERTAIN:
        return INFLUX_QUALITY_UNCERTAIN
    return INFLUX_QUALITY_BAD


def opc_quality_label(opc_quality: Optional[int]) -> str:
    """OPC quality 정수값을 사람이 읽기 쉬운 레이블로 변환."""
    if opc_quality == OPC_QUALITY_GOOD:
        return "GOOD"
    if opc_quality == OPC_QUALITY_UNCERTAIN:
        return "UNCERTAIN"
    return "BAD"


def compute_integ_final_value(
    raw_val: Optional[float],
    cond_val: Optional[float],
    final_quality: int,
    integ_status: str,
    reasons: List[str],
    reason_mask: Optional[int] = None,
) -> Optional[float]:
    """upper_kafka/contract.py `final_value()`와 동일한 예비 계산 규칙.
    실제 수신 경로에서는 메시지에 실린 `final_val`을 그대로 사용한다.
    - 품질 0(BAD)이면 None (NULL)
    - mask & 48 (OUTLIER_REPLACED=0x10 | LOCF_HELD=0x20)이면 cond_val
    - 그 밖은 raw_val
    """
    if int(final_quality) == OPC_QUALITY_BAD:
        return None
    if reason_mask is not None and reason_mask > 0:
        return cond_val if (reason_mask & 48) else raw_val
    reason_set = {r.upper() for r in (reasons or [])}
    if "OUTLIER_REPLACED" in reason_set or "LOCF_HELD" in reason_set:
        return cond_val
    return raw_val


# ---------------------------------------------------------------------------
# 토픽별 표준 페이로드 데이터클래스 및 파서
# ---------------------------------------------------------------------------
@dataclass
class EdgeTelemetryVQT:
    """edgeex.telemetry.vqt / edgeex.test.telemetry.vqt 토픽 메시지 규격."""

    site_id: str
    tag_id: str
    ts_ms: int
    raw_val: Optional[float]
    cond_val: Optional[float]
    final_val: Optional[float] = None
    final_quality: int = OPC_QUALITY_GOOD  # edgeEX OPC quality (2=GOOD, 1=UNCERTAIN, 0=BAD)
    quality: int = OPC_QUALITY_GOOD        # 하위 호환 별칭 (= final_quality)
    integ_class: int = 0                   # 0~5
    integ_status: str = "NORMAL"           # NORMAL|OUTLIER_SUPPRESSED|MISSING_HELD|STALE_ALARM|HUNTING_DETECTED|COLLECTION_STOPPED
    reasons: List[str] = field(default_factory=list)
    reason_mask: int = 0
    channel: str = "default"
    unit: str = ""
    tag_type: str = "analog"
    diff_abs: float = 0.0
    is_imputed: bool = False
    alarm_event: str = "NONE"
    consistency: str = "UNVERIFIED"
    eval_desc: str = ""

    @property
    def dedup_key(self) -> Tuple[str, str, int]:
        """at-least-once 중복 흡수용 고유 키 (site_id, tag_id, ts_ms)."""
        return (self.site_id, self.tag_id, self.ts_ms)

    @property
    def timestamp(self) -> datetime:
        """부동소수점 나눗셈 오차 없이 정수 밀리초(ts_ms)를 정확한 UTC datetime으로 변환."""
        return _EPOCH_UTC + timedelta(milliseconds=int(self.ts_ms))

    @property
    def influx_value(self) -> Optional[float]:
        """influx_hist 적재용 최종값 (오너 결정: INTEG final_val; 품질 0이면 None)."""
        if self.final_quality == OPC_QUALITY_BAD:
            return None
        return float(self.final_val) if self.final_val is not None else None

    @property
    def influx_quality(self) -> int:
        """influx_hist 적재용 quality (0=정상, 1=불확실, 2=불량)."""
        return opc_quality_to_influx(self.final_quality)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EdgeTelemetryVQT":
        tag_id = str(data.get("tag_id") or data.get("tag") or "UNKNOWN")
        ts_raw = data.get("ts_ms") if "ts_ms" in data else data.get("ts")
        if isinstance(ts_raw, int):
            ts_ms = ts_raw * 1000 if ts_raw < 100_000_000_000 else ts_raw
        elif isinstance(ts_raw, float):
            ts_ms = int(ts_raw * 1000) if ts_raw < 1e11 else int(ts_raw)
        elif isinstance(ts_raw, str):
            try:
                dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                ts_ms = int(dt.timestamp() * 1000)
            except ValueError:
                ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        else:
            ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        raw_v = data.get("raw_val") if "raw_val" in data else data.get("raw_value", data.get("value"))
        cond_v = data.get("cond_val") if "cond_val" in data else data.get("cond_value")

        raw_float = float(raw_v) if (raw_v is not None and raw_v != "") else None
        cond_float = float(cond_v) if (cond_v is not None and cond_v != "") else None

        fq_raw = data.get("final_quality") if "final_quality" in data else data.get("quality", OPC_QUALITY_GOOD)
        final_quality = int(fq_raw) if fq_raw is not None else OPC_QUALITY_BAD

        raw_status = data.get("integ_status")
        raw_class = data.get("integ_class")
        if raw_class is not None and int(raw_class) in INTEG_CLASS_TO_STATUS:
            integ_class = int(raw_class)
            integ_status = str(raw_status) if raw_status in INTEG_STATUS_TO_CLASS else INTEG_CLASS_TO_STATUS[integ_class]
        elif isinstance(raw_status, str) and raw_status in INTEG_STATUS_TO_CLASS:
            integ_status = raw_status
            integ_class = INTEG_STATUS_TO_CLASS[integ_status]
        else:
            integ_class = 0
            integ_status = "NORMAL"

        reason_mask = int(data.get("reason_mask", 0))
        raw_reasons = data.get("reasons")
        if isinstance(raw_reasons, list):
            reasons = [str(r) for r in raw_reasons]
        else:
            reasons = decode_reason_mask(reason_mask)

        # 판정 기준은 메시지에 실린 final_val이다 (§2-F)
        if int(final_quality) == OPC_QUALITY_BAD:
            final_float = None
        elif "final_val" in data:
            fv = data.get("final_val")
            final_float = float(fv) if (fv is not None and fv != "") else None
        else:
            final_float = compute_integ_final_value(
                raw_val=raw_float,
                cond_val=cond_float,
                final_quality=final_quality,
                integ_status=integ_status,
                reasons=reasons,
                reason_mask=reason_mask if "reason_mask" in data else None,
            )

        diff_abs = (
            float(data["diff_abs"])
            if data.get("diff_abs") is not None
            else (round(abs(cond_float - raw_float), 3) if (cond_float is not None and raw_float is not None) else 0.0)
        )
        is_imputed = bool(
            data.get(
                "is_imputed",
                integ_status in ("OUTLIER_SUPPRESSED", "MISSING_HELD")
                or any(r in ("LOCF_HELD", "OUTLIER_REPLACED") for r in reasons),
            )
        )

        return cls(
            site_id=str(data.get("site_id") or "poongdo-edge-01"),
            tag_id=tag_id,
            ts_ms=ts_ms,
            raw_val=raw_float,
            cond_val=cond_float,
            final_val=final_float,
            final_quality=final_quality,
            quality=final_quality,
            integ_class=integ_class,
            integ_status=integ_status,
            reasons=reasons,
            reason_mask=reason_mask,
            channel=str(data.get("channel") or "xgt_plc"),
            unit=str(data.get("unit") or ""),
            tag_type=str(data.get("tag_type") or "analog"),
            diff_abs=diff_abs,
            is_imputed=is_imputed,
            alarm_event=str(data.get("alarm_event") or "NONE"),
            consistency=str(data.get("consistency") or "UNVERIFIED"),
            eval_desc=str(data.get("eval_desc") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EdgeAlarmEvent:
    """edgeex.alarms.events / edgeex.test.alarms.events 토픽 메시지 규격 -> alarm_history 매핑."""

    event_id: str
    site_id: str
    tag_id: str
    level: int  # 1=CAUTION, 2=INFO/LOW, 3=WARNING/P3, 4=ERROR/HIGH/P2, 5=CRITICAL/HIHI/P1
    message: str
    value: float
    unit: str = ""
    sensor_type: str = "analog"
    threshold_low: Optional[float] = None
    threshold_high: Optional[float] = None
    cause: str = ""
    triggered_at_ms: int = 0
    acknowledged: bool = False
    resolved: bool = False
    scenario_id: str = "EDGEEX_ISA18"
    alarm_id: str = ""
    occurrence_id: str = ""
    event_type: str = "alarm_raise"

    @property
    def triggered_at(self) -> datetime:
        if self.triggered_at_ms > 0:
            return _EPOCH_UTC + timedelta(milliseconds=int(self.triggered_at_ms))
        return datetime.now(timezone.utc)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EdgeAlarmEvent":
        ts_raw = data.get("ts_ms") or data.get("triggered_at_ms") or data.get("ts")
        if isinstance(ts_raw, int):
            ts_ms = ts_raw * 1000 if ts_raw < 100_000_000_000 else ts_raw
        elif isinstance(ts_raw, float):
            ts_ms = int(ts_raw * 1000) if ts_raw < 1e11 else int(ts_raw)
        elif isinstance(ts_raw, str):
            try:
                dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                ts_ms = int(dt.timestamp() * 1000)
            except ValueError:
                ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        else:
            ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        detail = data.get("detail") if isinstance(data.get("detail"), dict) else {}
        raw_tag = data.get("tag_id") or data.get("tag") or detail.get("tag") or detail.get("tag_id")
        alarm_id = str(data.get("alarm_id") or "")
        # 태그 없는 체계 경보(tag_id: null)는 '__SYSTEM__'으로 표기
        tag_id = str(raw_tag) if raw_tag else "__SYSTEM__"
        site_id = str(data.get("site_id") or "poongdo-edge-01")
        event_name = str(data.get("event") or "alarm_raise")
        occ_id = str(data.get("occurrence_id") or "")
        raw_event_id = str(
            data.get("event_id")
            or data.get("id")
            or (f"{occ_id}:{event_name}" if occ_id else f"edgeex-{site_id}-{tag_id}-{ts_ms}")
        )
        max_len = int(os.getenv("KAFKA_EVENT_ID_MAX_LEN", "64"))
        event_id = raw_event_id[:max_len]

        raw_level = data.get("level") or data.get("priority") or 3
        if isinstance(raw_level, str):
            sev_map = {
                "CAUTION": 1,
                "LOW": 2,
                "LO": 2,
                "INFO": 2,
                "P3": 3,
                "WARNING": 3,
                "MEDIUM": 3,
                "P2": 4,
                "ERROR": 4,
                "HIGH": 4,
                "HI": 4,
                "LOLO": 5,
                "HIHI": 5,
                "P1": 5,
                "CRITICAL": 5,
            }
            level = sev_map.get(raw_level.upper(), 3)
        else:
            level = max(1, min(5, int(raw_level)))

        causes_list = detail.get("causes") if isinstance(detail.get("causes"), list) else []
        default_cause = (
            ",".join(str(c) for c in causes_list)
            if causes_list
            else str(data.get("source") or alarm_id or "edgeEX core/alarms.py")
        )

        val_raw = data.get("value") if data.get("value") is not None else detail.get("value")
        val_float = float(val_raw) if (val_raw is not None and val_raw != "") else 0.0

        return cls(
            event_id=event_id,
            site_id=site_id,
            tag_id=tag_id,
            level=level,
            message=str(data.get("message") or f"[{site_id}] {alarm_id or tag_id} ({event_name})"),
            value=val_float,
            unit=str(data.get("unit") or detail.get("unit") or ""),
            sensor_type=str(data.get("sensor_type") or data.get("tag_type") or detail.get("type") or "analog"),
            threshold_low=float(data["threshold_low"]) if data.get("threshold_low") is not None else None,
            threshold_high=float(data["threshold_high"]) if data.get("threshold_high") is not None else None,
            cause=str(data.get("cause") or data.get("alarm_type") or default_cause),
            triggered_at_ms=ts_ms,
            acknowledged=bool(data.get("acknowledged", False)),
            resolved=bool(data.get("resolved", False)),
            scenario_id=str(data.get("scenario_id") or "EDGEEX_ISA18"),
            alarm_id=alarm_id,
            occurrence_id=occ_id,
            event_type=event_name,
        )

    def to_sensor_data_json(self) -> Dict[str, Any]:
        """alarm_history.sensor_data JSONB 컬럼 포맷 생성."""
        return {
            "tag_name": self.tag_id,
            "alarm_id": self.alarm_id,
            "occurrence_id": self.occurrence_id,
            "event": self.event_type,
            "site_id": self.site_id,
            "sensor_type": self.sensor_type,
            "value": self.value,
            "unit": self.unit,
            "threshold_low": self.threshold_low,
            "threshold_high": self.threshold_high,
            "cause": self.cause,
            "source": "edgeEX",
        }


@dataclass
class EdgeHealthStatus:
    """edgeex.health.status / edgeex.test.health.status 토픽 메시지 규격."""

    site_id: str
    ts_ms: int
    status: str = "OK"
    pid: int = 0
    liveness: str = "OK"
    mem: Dict[str, Any] = field(default_factory=dict)
    uptime_s: float = 0.0
    stats: Dict[str, int] = field(default_factory=lambda: {"in": 0, "out": 0, "dropped": 0, "errors": 0})
    channels: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    ntp: Dict[str, Any] = field(default_factory=lambda: {"ok": True, "offset_ms": 0.0, "server": "pool.ntp.org"})
    config_sha256: str = ""
    tsdb_written: int = 0
    tsdb_buffered: int = 0
    tsdb_lost: int = 0
    p1_count: int = 0
    p2_count: int = 0
    p3_count: int = 0
    unacked_count: int = 0
    integ_stats: Dict[str, int] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EdgeHealthStatus":
        ts_raw = data.get("ts_ms") or data.get("ts")
        if isinstance(ts_raw, (int, float)):
            ts_ms = int(ts_raw * 1000) if ts_raw < 1e11 else int(ts_raw)
        else:
            ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        inner = data.get("payload") if isinstance(data.get("payload"), dict) else data
        status_str = str(data.get("status") or inner.get("liveness") or "OK")

        return cls(
            site_id=str(data.get("site_id") or "poongdo-edge-01"),
            ts_ms=ts_ms,
            status=status_str,
            pid=int(inner.get("pid") or 0),
            liveness=str(inner.get("liveness") or status_str),
            mem=dict(inner.get("mem") or {}),
            uptime_s=float(inner.get("uptime_s") or 0.0),
            stats=dict(inner.get("stats") or {"in": 0, "out": 0, "dropped": 0, "errors": 0}),
            channels=dict(inner.get("channels") or inner.get("channel_status") or {}),
            ntp=dict(inner.get("ntp") or {"ok": True, "offset_ms": 0.0, "server": "pool.ntp.org"}),
            config_sha256=str(inner.get("config_sha256") or ""),
            tsdb_written=int(inner.get("tsdb_written") or 0),
            tsdb_buffered=int(inner.get("tsdb_buffered") or 0),
            tsdb_lost=int(inner.get("tsdb_lost") or 0),
            p1_count=int(inner.get("p1_count") or 0),
            p2_count=int(inner.get("p2_count") or 0),
            p3_count=int(inner.get("p3_count") or 0),
            unacked_count=int(inner.get("unacked_count") or 0),
            integ_stats=dict(inner.get("integ_stats") or {}),
            payload=dict(inner),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
