"""
edgeEX 상위 관제 비즈니스 로직 서비스 (`edgeex_app/services/edge_monitor_service.py` — v1.6 DB 직결 + 브릿지 통합).

역할:
  - TimescaleDB(`public.edgeex_vqt_raw`, `public.alarm_history`, `public.edgeex_health_latest`, `public.influx_hist`),
    Consumer 상태 파일(`logs/consumer_metrics.json`), 인메모리 `EdgeMonitorBuffer`를 통합 조회하여
    별도 프로세스로 Consumer가 돌거나 웹 앱만 재시작된 경우에도 100% 정확한 실측 적재 데이터를 반환한다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from edgeex_app.integration.kafka_config import opc_quality_label
from edgeex_app.integration.kafka_consumer import get_edge_monitor_buffer
from edgeex_app.queries.edge_monitor import (
    query_edge_alarms,
    query_edgeex_health_latest,
    query_edgeex_vqt_latest_by_tag,
    query_edgeex_vqt_recent_rows,
    query_edgeex_vqt_summary_counts,
    query_edgeex_vqt_tag_series,
)


def _fmt_num(val: Any, null_label: str = "NULL") -> str:
    if val is None:
        return null_label
    try:
        return f"{float(val):.2f}"
    except Exception:
        return str(val)


def _quality_severity(fq: int) -> str:
    if fq == 2:
        return "success"
    if fq == 1:
        return "warning"
    return "error"


class EdgeMonitorService:
    """edgeEX 상위 모니터링 데이터 어셈블리 서비스."""

    def __init__(self, session: Any = None):
        self.session = session
        self.buffer = get_edge_monitor_buffer()

    def _read_status_file(self) -> Dict[str, Any]:
        status_path = Path(os.getenv("KAFKA_CONSUMER_STATUS_FILE", "logs/consumer_metrics.json"))
        if not status_path.is_file():
            return {}
        try:
            return json.loads(status_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    async def ensure_initial_data(self, min_points: int = 0) -> None:
        """실제 DB 적재 데이터를 우선하며, 가짜 시드 데이터를 자동 주입하지 않는다."""
        return None

    async def get_dashboard_snapshot(self, selected_tag: Optional[str] = None) -> Dict[str, Any]:
        """상위 관제 화면 전체 스냅샷을 plain dict로 반환."""
        buf = self.buffer
        status_file_data = self._read_status_file()
        file_metrics = status_file_data.get("metrics", {})
        file_health = status_file_data.get("site_health", {})

        # 1. DB 집계 및 테이블 조회
        counts = await query_edgeex_vqt_summary_counts()
        db_latest_tags = await query_edgeex_vqt_latest_by_tag()
        db_recent_rows = await query_edgeex_vqt_recent_rows(limit=50)
        db_alarms = await query_edge_alarms(limit=20)
        db_health_rows = await query_edgeex_health_latest()

        total_rows = int(counts.get("total_rows") or 0)
        bad_null_rows = int(counts.get("bad_quality_null_rows") or 0)
        bad_rows = int(counts.get("bad_rows") or 0)
        uncertain_rows = int(counts.get("uncertain_rows") or 0)
        good_rows = int(counts.get("good_rows") or 0)

        class_0 = int(counts.get("class_0_normal") or 0)
        class_1 = int(counts.get("class_1_outlier_suppressed") or 0)
        class_2 = int(counts.get("class_2_missing_held") or 0)
        class_3 = int(counts.get("class_3_stale_alarm") or 0)
        class_4 = int(counts.get("class_4_hunting_detected") or 0)
        class_5 = int(counts.get("class_5_collection_stopped") or 0)

        # 2. 태그별 최신 스냅샷 테이블 (DB 우선, 인메모리 보조)
        tag_rows: List[Dict[str, Any]] = []
        available_tags: List[str] = []

        if db_latest_tags:
            for r in db_latest_tags:
                t_id = str(r.get("tag_id") or "")
                if t_id and t_id not in available_tags:
                    available_tags.append(t_id)
                fq = int(r.get("final_quality") if r.get("final_quality") is not None else 2)
                raw_v = r.get("raw_val")
                cond_v = r.get("cond_val")
                final_v = r.get("final_val")
                diff_v = abs(float(cond_v) - float(raw_v)) if (cond_v is not None and raw_v is not None) else 0.0
                ts_obj = r.get("ts")
                ts_str = ts_obj.astimezone().strftime("%H:%M:%S") if ts_obj else str(r.get("ts_ms") or "-")
                reasons_csv = str(r.get("reasons_csv") or "")
                integ_cls = int(r.get("integ_class") or 0)
                integ_st = str(r.get("integ_status") or "NORMAL")

                tag_rows.append({
                    "tag_id": t_id,
                    "site_id": str(r.get("site_id") or "poongdo-edge-01"),
                    "channel": str(r.get("channel") or "default"),
                    "ts_ms": str(r.get("ts_ms") or "-"),
                    "raw_val": _fmt_num(raw_v, "NULL"),
                    "cond_val": _fmt_num(cond_v, "NULL"),
                    "final_val": _fmt_num(final_v, "NULL (BAD)" if fq == 0 else "NULL"),
                    "diff_abs": f"{diff_v:.2f}",
                    "unit": str(r.get("unit") or ""),
                    "final_quality": str(fq),
                    "quality_label": f"{opc_quality_label(fq)} ({fq})",
                    "quality_severity": _quality_severity(fq),
                    "influx_quality": str(r.get("influx_quality") if r.get("influx_quality") is not None else 0),
                    "integ_class": str(integ_cls),
                    "integ_status": f"{integ_cls}:{integ_st}",
                    "integ_severity": "success" if integ_cls == 0 else ("error" if fq == 0 or integ_cls in (3, 5) else "warning"),
                    "reasons": reasons_csv if reasons_csv else "NONE",
                    "eval_desc": f"final={_fmt_num(final_v, 'NULL')} | quality={fq} | reasons={reasons_csv or 'NONE'}",
                    "time": ts_str,
                })
        else:
            for t_id, v in sorted(buf.latest_vqt.items()):
                available_tags.append(t_id)
                fq = int(v.get("final_quality", v.get("quality", 2)))
                raw_v = v.get("raw_val")
                cond_v = v.get("cond_val")
                final_v = v.get("final_val")
                reasons_list = v.get("reasons") or []
                reasons_csv = ",".join(str(x) for x in reasons_list)
                integ_cls = int(v.get("integ_class", 0))
                integ_st = str(v.get("integ_status", "NORMAL"))
                tag_rows.append({
                    "tag_id": t_id,
                    "site_id": str(v.get("site_id", "poongdo-edge-01")),
                    "channel": str(v.get("channel", "default")),
                    "ts_ms": str(v.get("ts_ms", "-")),
                    "raw_val": _fmt_num(raw_v, "NULL"),
                    "cond_val": _fmt_num(cond_v, "NULL"),
                    "final_val": _fmt_num(final_v, "NULL (BAD)" if fq == 0 else "NULL"),
                    "diff_abs": f"{float(v.get('diff_abs', 0.0)):.2f}",
                    "unit": str(v.get("unit", "")),
                    "final_quality": str(fq),
                    "quality_label": f"{opc_quality_label(fq)} ({fq})",
                    "quality_severity": _quality_severity(fq),
                    "influx_quality": str(v.get("influx_quality", 0)),
                    "integ_class": str(integ_cls),
                    "integ_status": f"{integ_cls}:{integ_st}",
                    "integ_severity": "success" if integ_cls == 0 else ("error" if fq == 0 or integ_cls in (3, 5) else "warning"),
                    "reasons": reasons_csv if reasons_csv else "NONE",
                    "eval_desc": f"final={_fmt_num(final_v, 'NULL')} | quality={fq} | reasons={reasons_csv or 'NONE'}",
                    "time": str(v.get("time", "-")),
                })

        active_tag = selected_tag if (selected_tag and selected_tag in available_tags) else (available_tags[0] if available_tags else "")

        # 3. 최근 VQT 무손실 적재 이력 (edgeex_vqt_raw 전수 표본 — 8행 연기 시험 시 8행 모두 표시)
        recent_feed: List[Dict[str, Any]] = []
        for r in db_recent_rows:
            fq = int(r.get("final_quality") if r.get("final_quality") is not None else 2)
            raw_v = r.get("raw_val")
            cond_v = r.get("cond_val")
            final_v = r.get("final_val")
            ts_obj = r.get("ts")
            ts_str = ts_obj.astimezone().strftime("%H:%M:%S") if ts_obj else str(r.get("ts_ms") or "-")
            reasons_csv = str(r.get("reasons_csv") or "")
            integ_cls = int(r.get("integ_class") or 0)
            integ_st = str(r.get("integ_status") or "NORMAL")
            recent_feed.append({
                "time": ts_str,
                "ts_ms": str(r.get("ts_ms") or "-"),
                "site_id": str(r.get("site_id") or "poongdo-edge-01"),
                "tag_id": str(r.get("tag_id") or ""),
                "raw_val": _fmt_num(raw_v, "NULL"),
                "cond_val": _fmt_num(cond_v, "NULL"),
                "final_val": _fmt_num(final_v, "NULL (BAD)" if fq == 0 else "NULL"),
                "final_quality": str(fq),
                "quality_label": f"{opc_quality_label(fq)} ({fq})",
                "quality_severity": _quality_severity(fq),
                "influx_quality": str(r.get("influx_quality") if r.get("influx_quality") is not None else 0),
                "integ_class": str(integ_cls),
                "integ_status": f"{integ_cls}:{integ_st}",
                "integ_severity": "success" if integ_cls == 0 else ("error" if fq == 0 or integ_cls in (3, 5) else "warning"),
                "reasons": reasons_csv if reasons_csv else "NONE",
            })

        # 4. 선택된 태그의 시계열 차트 데이터
        chart_series: List[Dict[str, Any]] = []
        if active_tag:
            series_rows = await query_edgeex_vqt_tag_series(active_tag, limit=60)
            for row in reversed(series_rows):
                ts_obj = row.get("ts")
                raw_v = row.get("raw_val")
                cond_v = row.get("cond_val")
                final_v = row.get("final_val")
                fv_num = float(final_v) if final_v is not None else (float(cond_v) if cond_v is not None else 0.0)
                rv_num = float(raw_v) if raw_v is not None else fv_num
                chart_series.append({
                    "time": ts_obj.astimezone().strftime("%H:%M:%S") if ts_obj else str(row.get("ts_ms") or ""),
                    "raw_val": rv_num,
                    "cond_val": fv_num,
                    "diff_abs": round(abs(fv_num - rv_num), 3),
                    "status": str(row.get("integ_status") or "NORMAL"),
                })

        # 5. 경보 목록 (alarm_history)
        alarms_list: List[Dict[str, Any]] = []
        for a in db_alarms:
            ts_obj = a.get("triggered_at")
            alarms_list.append({
                "event_id": str(a.get("event_id") or ""),
                "time": ts_obj.astimezone().strftime("%H:%M:%S") if ts_obj else str(a.get("triggered_at_ms") or "-"),
                "triggered_at_ms": str(a.get("triggered_at_ms") or "-"),
                "site_id": str(a.get("site_id") or "poongdo-edge-01"),
                "tag_id": str(a.get("tag_name") or "__SYSTEM__"),
                "alarm_id": str(a.get("alarm_id") or ""),
                "level": str(a.get("level") or 3),
                "message": str(a.get("message") or ""),
                "value": _fmt_num(a.get("value"), "0.00"),
                "unit": str(a.get("unit") or ""),
                "cause": str(a.get("cause") or ""),
                "acknowledged": "ACK" if a.get("acknowledged") else "UNACK",
                "resolved": "CLEAR" if a.get("resolved") else "ACTIVE",
                "severity": "info" if a.get("resolved") else "alarm",
            })

        # 6. /health 스냅샷 (DB edgeex_health_latest + consumer_metrics.json + 인메모리 통합)
        sites_list: List[Dict[str, Any]] = []
        channels_list: List[Dict[str, Any]] = []
        ntp_offset_ms = 0.0
        ntp_ok = True
        ntp_server = "pool.ntp.org"

        for hr in db_health_rows:
            s_id = str(hr.get("site_id") or "edge-acceptance")
            ts_obj = hr.get("ts")
            ts_str = ts_obj.astimezone().strftime("%H:%M:%S") if ts_obj else str(hr.get("ts_ms") or "-")
            st_val = str(hr.get("status") or "OK")
            live_val = str(hr.get("liveness") or st_val)
            raw_json = str(hr.get("payload_json") or "{}")
            try:
                p_dict = json.loads(raw_json)
            except Exception:
                p_dict = {}
            inner = p_dict.get("payload") if isinstance(p_dict.get("payload"), dict) else p_dict
            ntp_info = inner.get("ntp") if isinstance(inner.get("ntp"), dict) else {}
            if ntp_info:
                ntp_offset_ms = float(ntp_info.get("offset_ms", 0.0))
                ntp_ok = bool(ntp_info.get("ok", True))
                ntp_server = str(ntp_info.get("server", "pool.ntp.org"))

            ch_map = inner.get("channels") if isinstance(inner.get("channels"), dict) else {}
            for ch_name, ch_info in ch_map.items():
                if isinstance(ch_info, dict):
                    ch_ok = bool(ch_info.get("ok", True))
                    channels_list.append({
                        "site_id": s_id,
                        "channel": str(ch_name),
                        "protocol": str(ch_info.get("protocol", "Industrial")),
                        "ok": ch_ok,
                        "latency_ms": f"{float(ch_info.get('latency_ms', 0.0)):.1f}",
                        "tags_polled": str(ch_info.get("tags_polled", 0)),
                        "errors": str(ch_info.get("errors", 0)),
                        "status": "GOOD" if ch_ok else "ERROR",
                    })

            sites_list.append({
                "site_id": s_id,
                "status": st_val,
                "liveness": live_val,
                "ts_ms": str(hr.get("ts_ms") or "-"),
                "updated_at": ts_str,
                "summary": raw_json[:160],
            })

        if not sites_list:
            merged_mem_health = {**file_health, **buf.site_health}
            for s_id, h in merged_mem_health.items():
                sites_list.append({
                    "site_id": str(s_id),
                    "status": str(h.get("status") or h.get("liveness") or "OK"),
                    "liveness": str(h.get("liveness") or "OK"),
                    "ts_ms": "-",
                    "updated_at": str(h.get("updated_at") or "-"),
                    "summary": json.dumps(h, ensure_ascii=False)[:160],
                })

        # 7. 메트릭 및 KPI 조합
        merged_metrics = dict(buf.metrics)
        if file_metrics:
            merged_metrics.update(file_metrics)
        if total_rows > 0:
            merged_metrics["vqt_raw_rows_written"] = max(int(merged_metrics.get("vqt_raw_rows_written") or 0), total_rows)
            merged_metrics["bad_quality_preserved"] = max(int(merged_metrics.get("bad_quality_preserved") or 0), bad_null_rows)
            if merged_metrics.get("broker_status") in ("STANDBY", None):
                merged_metrics["broker_status"] = "CONNECTED"

        quality_ratio = round((good_rows / total_rows) * 100.0, 1) if total_rows > 0 else 100.0
        health_count = max(len(sites_list), int(merged_metrics.get("health_count") or 0))
        health_status_label = sites_list[0]["status"] if sites_list else "STANDBY"
        active_site_id = sites_list[0]["site_id"] if sites_list else (tag_rows[0]["site_id"] if tag_rows else "edge-acceptance")

        return {
            "available_tags": available_tags,
            "selected_tag": active_tag,
            "metrics": merged_metrics,
            "sites": sites_list,
            "channels": channels_list,
            "tag_rows": tag_rows,
            "chart_series": chart_series,
            "recent_feed": recent_feed,
            "recent_alarms": alarms_list,
            "kpi": {
                "site_count": max(len(sites_list), int(counts.get("site_count") or 0), 1 if total_rows > 0 else 0),
                "active_site_id": active_site_id,
                "tag_count": len(tag_rows),
                "vqt_total_rows": total_rows,
                "good_quality_rows": good_rows,
                "uncertain_quality_rows": uncertain_rows,
                "bad_quality_rows": bad_rows,
                "bad_quality_null_rows": bad_null_rows,
                "duplicates_absorbed": int(merged_metrics.get("duplicates_absorbed") or 0),
                "commits_succeeded": int(merged_metrics.get("commits_succeeded") or 0),
                "quality_ratio": f"{quality_ratio:.1f}",
                "total_evaluated": total_rows,
                "protection_count": class_1 + class_2,
                "class_0_normal": class_0,
                "spike_suppressed": class_1,
                "missing_held": class_2,
                "stale_alarms": class_3,
                "hunting_detected": class_4,
                "collection_stopped": class_5,
                "process_alarms": len(alarms_list),
                "health_count": health_count,
                "health_status": health_status_label,
                "ntp_offset_ms": f"{ntp_offset_ms:.1f}",
                "ntp_ok": ntp_ok,
                "ntp_server": ntp_server,
            },
        }
