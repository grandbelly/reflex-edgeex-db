"""
edgeEX 상위 모니터링 전용 Raw SQL 조회 모듈 (`edgeex_app/queries/edge_monitor.py`).

계약(edgeex_app/queries/AGENTS.md):
  - Raw SQL only (`db.q()`), 비즈니스 로직 없음.
  - 무손실 원본/최종값 테이블(`public.edgeex_vqt_raw`), `public.alarm_history`,
    `public.edgeex_health_latest`, `public.influx_hist`에서 적재 현황을 직접 조회.
"""
from __future__ import annotations

from typing import Any, Dict, List
from ..db import q


async def query_edgeex_vqt_summary_counts() -> Dict[str, Any]:
    """public.edgeex_vqt_raw 의 전체 행수, 품질별 행수(BAD 포함), INTEG 클래스(0~5) 건수를 집계."""
    sql = """
        SELECT
            COUNT(*)::BIGINT AS total_rows,
            COUNT(*) FILTER (WHERE final_quality = 0 AND final_val IS NULL)::BIGINT AS bad_quality_null_rows,
            COUNT(*) FILTER (WHERE final_quality = 0)::BIGINT AS bad_rows,
            COUNT(*) FILTER (WHERE final_quality = 1)::BIGINT AS uncertain_rows,
            COUNT(*) FILTER (WHERE final_quality = 2)::BIGINT AS good_rows,
            COUNT(*) FILTER (WHERE integ_class = 0)::BIGINT AS class_0_normal,
            COUNT(*) FILTER (WHERE integ_class = 1)::BIGINT AS class_1_outlier_suppressed,
            COUNT(*) FILTER (WHERE integ_class = 2)::BIGINT AS class_2_missing_held,
            COUNT(*) FILTER (WHERE integ_class = 3)::BIGINT AS class_3_stale_alarm,
            COUNT(*) FILTER (WHERE integ_class = 4)::BIGINT AS class_4_hunting_detected,
            COUNT(*) FILTER (WHERE integ_class = 5)::BIGINT AS class_5_collection_stopped,
            COUNT(DISTINCT site_id)::BIGINT AS site_count,
            COUNT(DISTINCT tag_id)::BIGINT AS tag_count
        FROM public.edgeex_vqt_raw
    """
    try:
        rows = await q(sql, ())
        return rows[0] if rows else {}
    except Exception:
        return {}


async def query_edgeex_vqt_latest_by_tag() -> List[Dict[str, Any]]:
    """public.edgeex_vqt_raw 에서 태그별 최신 VQT 스냅샷(BAD 품질 0 포함)을 조회."""
    sql = """
        SELECT DISTINCT ON (tag_id)
            ts,
            trunc(EXTRACT(EPOCH FROM ts) * 1000)::BIGINT AS ts_ms,
            site_id,
            tag_id,
            channel,
            raw_val,
            cond_val,
            final_val,
            final_quality,
            influx_quality,
            integ_class,
            integ_status,
            reasons::TEXT AS reasons_json,
            COALESCE(
                (
                    SELECT string_agg(elem, ',' ORDER BY ord)
                    FROM jsonb_array_elements_text(reasons) WITH ORDINALITY AS t(elem, ord)
                ),
                ''
            ) AS reasons_csv,
            unit
        FROM public.edgeex_vqt_raw
        ORDER BY tag_id ASC, ts DESC
    """
    try:
        return await q(sql, ())
    except Exception:
        return []


async def query_edgeex_vqt_recent_rows(limit: int = 50) -> List[Dict[str, Any]]:
    """public.edgeex_vqt_raw 에서 최근 적재된 VQT 표본(BAD 품질 0 및 NULL 포함 전수)을 조회."""
    sql = """
        SELECT
            ts,
            trunc(EXTRACT(EPOCH FROM ts) * 1000)::BIGINT AS ts_ms,
            site_id,
            tag_id,
            channel,
            raw_val,
            cond_val,
            final_val,
            final_quality,
            influx_quality,
            integ_class,
            integ_status,
            COALESCE(
                (
                    SELECT string_agg(elem, ',' ORDER BY ord)
                    FROM jsonb_array_elements_text(reasons) WITH ORDINALITY AS t(elem, ord)
                ),
                ''
            ) AS reasons_csv,
            unit
        FROM public.edgeex_vqt_raw
        ORDER BY ts DESC, tag_id ASC
        LIMIT $1
    """
    try:
        return await q(sql, (limit,))
    except Exception:
        return []


async def query_edgeex_vqt_tag_series(tag_id: str, limit: int = 60) -> List[Dict[str, Any]]:
    """public.edgeex_vqt_raw 에서 특정 태그의 시계열 이력을 조회."""
    sql = """
        SELECT
            ts,
            trunc(EXTRACT(EPOCH FROM ts) * 1000)::BIGINT AS ts_ms,
            site_id,
            tag_id,
            raw_val,
            cond_val,
            final_val,
            final_quality,
            integ_class,
            integ_status
        FROM public.edgeex_vqt_raw
        WHERE tag_id = $1
        ORDER BY ts DESC
        LIMIT $2
    """
    try:
        return await q(sql, (tag_id, limit))
    except Exception:
        return []


async def query_edge_recent_hist(tag_name: str, limit: int = 60) -> List[Dict[str, Any]]:
    """influx_hist 에서 특정 태그의 최근 적재 이력을 조회."""
    sql = """
        SELECT
            ts,
            tag_name,
            value,
            quality
        FROM public.influx_hist
        WHERE tag_name = $1
        ORDER BY ts DESC
        LIMIT $2
    """
    try:
        return await q(sql, (tag_name, limit))
    except Exception:
        return []


async def query_edge_alarms(limit: int = 20) -> List[Dict[str, Any]]:
    """alarm_history 에서 최근 경보 사건 조회."""
    sql = """
        SELECT
            event_id,
            scenario_id,
            level,
            triggered_at,
            trunc(EXTRACT(EPOCH FROM triggered_at) * 1000)::BIGINT AS triggered_at_ms,
            message,
            COALESCE(sensor_data->>'tag_name', '__SYSTEM__') AS tag_name,
            COALESCE(sensor_data->>'alarm_id', '') AS alarm_id,
            COALESCE(sensor_data->>'site_id', 'poongdo-edge-01') AS site_id,
            COALESCE((sensor_data->>'value')::float8, 0.0) AS value,
            COALESCE(sensor_data->>'unit', '') AS unit,
            COALESCE(sensor_data->>'cause', '') AS cause,
            acknowledged,
            resolved
        FROM public.alarm_history
        ORDER BY triggered_at DESC
        LIMIT $1
    """
    try:
        return await q(sql, (limit,))
    except Exception:
        return []


async def query_edgeex_health_latest() -> List[Dict[str, Any]]:
    """public.edgeex_health_latest 에서 사이트별 최신 /health 스냅샷을 조회."""
    sql = """
        SELECT
            site_id,
            ts,
            trunc(EXTRACT(EPOCH FROM ts) * 1000)::BIGINT AS ts_ms,
            status,
            liveness,
            payload::TEXT AS payload_json,
            updated_at
        FROM public.edgeex_health_latest
        ORDER BY site_id ASC
    """
    return await q(sql, ())


async def query_edge_alarm_count() -> int:
    """경보 KPI는 최근 목록의 길이가 아니라 전체 저장 건수다."""
    rows = await q("SELECT COUNT(*)::BIGINT AS n FROM public.alarm_history", ())
    return int(rows[0]["n"]) if rows else 0
