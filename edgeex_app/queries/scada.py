"""Bounded, site-scoped read model. No DDL, ingestion, or legacy fallback."""
from datetime import datetime, timezone
from ..db import get_pool

VQT_COLUMNS = {
    "site_id", "tag_id", "ts", "ingested_at", "channel", "raw_val", "cond_val",
    "final_val", "final_quality", "reasons", "unit",
}


class ScadaQueryError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


async def read_snapshot(site: str, tag: str = "", minutes: int = 15) -> dict:
    if not site or len(site) > 200 or len(tag) > 300:
        raise ValueError("A bounded site_id is required")
    if minutes not in {5, 15, 60}:
        raise ValueError("Supported windows: 5, 15, 60 minutes")
    pool = await get_pool()
    async with pool.acquire(timeout=2) as conn:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            await conn.execute("SET LOCAL statement_timeout = '3000ms'")
            at = await conn.fetchval("SELECT transaction_timestamp()")
            columns = await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='edgeex_vqt_raw'"
            )
            if not VQT_COLUMNS <= {r["column_name"] for r in columns}:
                raise ScadaQueryError("VQT_SCHEMA_INCOMPATIBLE")
            latest = await conn.fetch(
                "SELECT DISTINCT ON (tag_id) site_id,tag_id,ts,ingested_at,channel,"
                "raw_val,cond_val,final_val,final_quality,reasons,unit "
                "FROM public.edgeex_vqt_raw WHERE site_id=$1 "
                "ORDER BY tag_id,ts DESC LIMIT 2001", site,
            )
            if len(latest) > 2000:
                raise ScadaQueryError("TAG_LIMIT_EXCEEDED")
            tags = {r["tag_id"] for r in latest}
            if tag and tag not in tags:
                raise ScadaQueryError("TAG_NOT_IN_SITE")
            selected = tag or next((r["tag_id"] for r in latest
                                    if r["final_val"] is not None), "")
            series = []
            if selected:
                series = await conn.fetch(
                    "SELECT ts,raw_val,cond_val,final_val,final_quality,reasons "
                    "FROM public.edgeex_vqt_raw WHERE site_id=$1 AND tag_id=$2 "
                    "AND ts >= $3::timestamptz - $4 * interval '1 minute' "
                    "AND ts <= $3 ORDER BY ts DESC LIMIT 2001",
                    site, selected, at, minutes,
                )
            counts = await conn.fetchrow(
                "SELECT count(*) AS received,"
                "count(*) FILTER (WHERE final_quality=2) AS good,"
                "count(*) FILTER (WHERE final_quality=1) AS uncertain,"
                "count(*) FILTER (WHERE final_quality=0) AS bad "
                "FROM public.edgeex_vqt_raw WHERE site_id=$1 "
                "AND ts >= $2::timestamptz - $3 * interval '1 minute' AND ts <= $2",
                site, at, minutes,
            )
            sections = {}
            # Optional failures roll back to a savepoint, leaving VQT available.
            for section, table, sql, args in (
                ("health", "edgeex_health_latest",
                 "SELECT site_id,ts,status,liveness,payload FROM public.edgeex_health_latest "
                 "WHERE site_id=$1", (site,)),
                ("alarms", "alarm_history",
                 "SELECT event_id,triggered_at,message,level,acknowledged,resolved,sensor_data "
                 "FROM public.alarm_history WHERE sensor_data->>'site_id'=$1 "
                 "ORDER BY triggered_at DESC LIMIT 100", (site,)),
            ):
                if not await conn.fetchval("SELECT to_regclass($1)", "public." + table):
                    sections[section] = {"state": "error", "code": "SCHEMA_MISSING", "rows": []}
                    continue
                try:
                    async with conn.transaction():
                        rows = await conn.fetch(sql, *args)
                    sections[section] = {"state": "ok", "code": "", "rows": [dict(r) for r in rows]}
                except Exception as exc:
                    sections[section] = {"state": "error", "code": getattr(exc, "sqlstate", None)
                                         or "QUERY_FAILED", "rows": []}
            return {
                "site_id": site, "as_of": at, "served_at": datetime.now(timezone.utc),
                "latest": [dict(r) for r in latest], "selected_tag": selected,
                "series": [dict(r) for r in reversed(series[:2000])],
                "series_truncated": len(series) > 2000,
                "counts": dict(counts), "sections": sections, "minutes": minutes,
            }
