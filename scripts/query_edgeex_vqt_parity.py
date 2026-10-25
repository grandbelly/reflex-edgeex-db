"""
Read-only parity verification query for Upper TimescaleDB (`public.edgeex_vqt_raw`).

Compares Upper `public.edgeex_vqt_raw` against Edge TSDB (`tag_raw` LEFT JOIN `tag_cond` -> `final_value()`)
using deterministic 64-bit hashes (`xor17`, `xor53`) and row counts over `(site_id, tag_id, ts_ms)`.

Key Guarantees (§2-G):
1. Strictly READ ONLY (`SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY`, `SET statement_timeout = 10000`).
2. Direct indexable timestamp predicates (`ts >= to_timestamp(start_ms / 1000.0) AND ts <= to_timestamp(end_ms / 1000.0)`).
3. 1-minute slice execution (`60_000 ms` per slice): computes count and `xor17`/`xor53` per 1-minute slice and
   combines them in Python (`total += slice_count`, `xor ^= slice_xor`) so large time windows never hit the 10s timeout.
4. Canonical Row Signature (`row_sig`) Specification (7 fields joined by `|`):
   `site_id|tag_id|ts_ms|final_val_str|final_quality|integ_class|reasons_csv`
   - `site_id`       : TEXT (e.g. `edge-acceptance`)
   - `tag_id`        : TEXT (e.g. `TAG_001`)
   - `ts_ms`         : `trunc(EXTRACT(EPOCH FROM ts) * 1000)::BIGINT::TEXT` (matches `int(ts.timestamp() * 1000)`)
   - `final_val_str` : `'NULL'` if `final_val IS NULL`, else `to_char(final_val, 'FM999999999990.000000000')` (fixed 9 decimal places)
   - `final_quality` : `final_quality::TEXT` (`0`, `1`, `2`)
   - `integ_class`   : `integ_class::TEXT` (`0`..`5`)
   - `reasons_csv`   : Comma-joined reason names in bit order 0..17 (`core/conditioning.py` `REASON_LABELS`), no spaces;
                       empty string `''` when no reason bits are set.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _load_env_file(env_path: Path) -> None:
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


BOUNDS_SQL = """
SELECT
    trunc(EXTRACT(EPOCH FROM MIN(ts)) * 1000)::BIGINT AS min_ts_ms,
    trunc(EXTRACT(EPOCH FROM MAX(ts)) * 1000)::BIGINT AS max_ts_ms
FROM public.edgeex_vqt_raw
WHERE (%s::TEXT IS NULL OR site_id = %s::TEXT)
  AND (%s::BIGINT IS NULL OR ts >= to_timestamp(%s::BIGINT / 1000.0))
  AND (%s::BIGINT IS NULL OR ts <= to_timestamp(%s::BIGINT / 1000.0));
"""


SLICE_PARITY_SQL = """
WITH scoped AS (
    SELECT
        r.site_id,
        r.tag_id,
        trunc(EXTRACT(EPOCH FROM r.ts) * 1000)::BIGINT AS ts_ms,
        CASE
            WHEN r.final_val IS NULL THEN 'NULL'
            ELSE to_char(r.final_val, 'FM999999999990.000000000')
        END AS final_val_str,
        r.final_val,
        r.final_quality,
        r.integ_class,
        COALESCE(
            (
                SELECT string_agg(elem, ',' ORDER BY ord)
                FROM jsonb_array_elements_text(r.reasons) WITH ORDINALITY AS t(elem, ord)
            ),
            ''
        ) AS reasons_csv
    FROM public.edgeex_vqt_raw r
    WHERE (%s::TEXT IS NULL OR r.site_id = %s::TEXT)
      AND r.ts >= to_timestamp(%s::BIGINT / 1000.0)
      AND r.ts <= to_timestamp(%s::BIGINT / 1000.0)
),
canonical AS (
    SELECT
        site_id,
        tag_id,
        ts_ms,
        final_val,
        final_quality,
        integ_class,
        concat_ws(
            '|',
            site_id,
            tag_id,
            ts_ms::TEXT,
            final_val_str,
            final_quality::TEXT,
            integ_class::TEXT,
            reasons_csv
        ) AS row_sig
    FROM scoped
)
SELECT
    COUNT(*)::BIGINT AS total_rows,
    COUNT(*) FILTER (WHERE final_quality = 0 AND final_val IS NULL)::BIGINT AS bad_quality_null_rows,
    COUNT(*) FILTER (WHERE final_quality = 0 AND final_val IS NOT NULL)::BIGINT AS bad_quality_non_null_violation_rows,
    COUNT(*) FILTER (WHERE integ_class = 0)::BIGINT AS class_0_normal,
    COUNT(*) FILTER (WHERE integ_class = 1)::BIGINT AS class_1_outlier_suppressed,
    COUNT(*) FILTER (WHERE integ_class = 2)::BIGINT AS class_2_missing_held,
    COUNT(*) FILTER (WHERE integ_class = 3)::BIGINT AS class_3_stale_alarm,
    COUNT(*) FILTER (WHERE integ_class = 4)::BIGINT AS class_4_hunting_detected,
    COUNT(*) FILTER (WHERE integ_class = 5)::BIGINT AS class_5_collection_stopped,
    COALESCE(bit_xor(hashtextextended(row_sig, 17)), 0)::BIGINT AS xor17,
    COALESCE(bit_xor(hashtextextended(row_sig, 53)), 0)::BIGINT AS xor53,
    MIN(ts_ms) AS min_ts_ms,
    MAX(ts_ms) AS max_ts_ms
FROM canonical;
"""


ALARM_PARITY_SQL = """
SELECT
    COUNT(*)::BIGINT AS total_alarms,
    COUNT(*) FILTER (WHERE sensor_data->>'tag_name' = '__SYSTEM__')::BIGINT AS tagless_system_alarms,
    COALESCE(
        bit_xor(
            hashtextextended(
                concat_ws(
                    '|',
                    event_id,
                    trunc(EXTRACT(EPOCH FROM triggered_at) * 1000)::BIGINT::TEXT,
                    COALESCE(sensor_data->>'tag_name', '__SYSTEM__'),
                    level::TEXT
                ),
                17
            )
        ),
        0
    )::TEXT AS alarm_xor17
FROM public.alarm_history
WHERE (%s::BIGINT IS NULL OR triggered_at >= to_timestamp(%s::BIGINT / 1000.0))
  AND (%s::BIGINT IS NULL OR triggered_at <= to_timestamp(%s::BIGINT / 1000.0));
"""


def _iter_minute_slices(start_ms: int, end_ms: int, slice_ms: int = 60_000) -> List[Tuple[int, int]]:
    """[start_ms, end_ms] 구간을 겹치지 않는 1분(60,000ms) 닫힌구간 [s, e] 목록으로 분할."""
    slices: List[Tuple[int, int]] = []
    cur = start_ms
    while cur <= end_ms:
        nxt = min(cur + slice_ms - 1, end_ms)
        slices.append((cur, nxt))
        cur = nxt + 1
    return slices


def _read_consumer_duplicates_absorbed(project_root: Path) -> Optional[int]:
    status_file = Path(os.getenv("KAFKA_CONSUMER_STATUS_FILE", str(project_root / "logs" / "consumer_metrics.json")))
    if not status_file.is_file():
        return None
    try:
        data = json.loads(status_file.read_text(encoding="utf-8"))
        val = data.get("metrics", {}).get("duplicates_absorbed")
        return int(val) if val is not None else None
    except Exception:
        return None


async def run_parity_query(
    dsn: str,
    site_id: Optional[str],
    start_ms: Optional[int],
    end_ms: Optional[int],
    duplicates_absorbed: Optional[int] = None,
    slice_ms: int = 60_000,
) -> Dict[str, Any]:
    conn = await psycopg.AsyncConnection.connect(dsn, autocommit=True)
    try:
        async with conn.cursor() as cur:
            await cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
            await cur.execute("SET statement_timeout = 10000;")

            # 1) Determine effective [window_start_ms, window_end_ms]
            effective_start = start_ms
            effective_end = end_ms
            if effective_start is None or effective_end is None:
                await cur.execute(
                    BOUNDS_SQL,
                    (site_id, site_id, start_ms, start_ms, end_ms, end_ms),
                )
                bounds_row = await cur.fetchone()
                if bounds_row and bounds_row[0] is not None and bounds_row[1] is not None:
                    if effective_start is None:
                        effective_start = int(bounds_row[0])
                    if effective_end is None:
                        effective_end = int(bounds_row[1])

            total_rows = 0
            bad_quality_null_rows = 0
            bad_quality_non_null_violation_rows = 0
            class_counts = {
                "0_NORMAL": 0,
                "1_OUTLIER_SUPPRESSED": 0,
                "2_MISSING_HELD": 0,
                "3_STALE_ALARM": 0,
                "4_HUNTING_DETECTED": 0,
                "5_COLLECTION_STOPPED": 0,
            }
            xor17_acc = 0
            xor53_acc = 0
            min_ts_ms: Optional[int] = None
            max_ts_ms: Optional[int] = None
            slice_summaries: List[Dict[str, Any]] = []

            if effective_start is not None and effective_end is not None and effective_start <= effective_end:
                slices = _iter_minute_slices(effective_start, effective_end, slice_ms=slice_ms)
                for s_ms, e_ms in slices:
                    await cur.execute(
                        SLICE_PARITY_SQL,
                        (site_id, site_id, s_ms, e_ms),
                    )
                    row = await cur.fetchone()
                    if not row:
                        continue
                    s_total = int(row[0])
                    total_rows += s_total
                    bad_quality_null_rows += int(row[1])
                    bad_quality_non_null_violation_rows += int(row[2])
                    class_counts["0_NORMAL"] += int(row[3])
                    class_counts["1_OUTLIER_SUPPRESSED"] += int(row[4])
                    class_counts["2_MISSING_HELD"] += int(row[5])
                    class_counts["3_STALE_ALARM"] += int(row[6])
                    class_counts["4_HUNTING_DETECTED"] += int(row[7])
                    class_counts["5_COLLECTION_STOPPED"] += int(row[8])
                    s_xor17 = int(row[9])
                    s_xor53 = int(row[10])
                    xor17_acc ^= s_xor17
                    xor53_acc ^= s_xor53

                    if row[11] is not None:
                        r_min = int(row[11])
                        min_ts_ms = r_min if min_ts_ms is None else min(min_ts_ms, r_min)
                    if row[12] is not None:
                        r_max = int(row[12])
                        max_ts_ms = r_max if max_ts_ms is None else max(max_ts_ms, r_max)

                    slice_summaries.append({
                        "slice_start_ms": s_ms,
                        "slice_end_ms": e_ms,
                        "rows": s_total,
                        "xor17": str(s_xor17),
                        "xor53": str(s_xor53),
                    })

            await cur.execute(
                ALARM_PARITY_SQL,
                (start_ms, start_ms, end_ms, end_ms),
            )
            alarm_row = await cur.fetchone()

        return {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "query_mode": "READ_ONLY_1MIN_SLICED",
            "filters": {
                "site_id": site_id,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "effective_start_ms": effective_start,
                "effective_end_ms": effective_end,
                "slice_ms": slice_ms,
                "slice_count": len(slice_summaries),
            },
            "canonical_signature_spec": {
                "format": "site_id|tag_id|ts_ms|final_val_str|final_quality|integ_class|reasons_csv",
                "field_order": [
                    "site_id",
                    "tag_id",
                    "ts_ms",
                    "final_val_str",
                    "final_quality",
                    "integ_class",
                    "reasons_csv",
                ],
                "null_notation": "NULL",
                "numeric_format": "to_char(final_val, 'FM999999999990.000000000')",
                "ts_ms_rule": "trunc(EXTRACT(EPOCH FROM ts) * 1000)::BIGINT::TEXT",
                "reasons_rule": "Comma-joined bit-order reason names (0..17 from core/conditioning.py REASON_LABELS), no spaces, empty string '' if none",
                "xor17": "COALESCE(bit_xor(hashtextextended(row_sig, 17)), 0)::BIGINT",
                "xor53": "COALESCE(bit_xor(hashtextextended(row_sig, 53)), 0)::BIGINT",
            },
            "edgeex_vqt_raw": {
                "total_rows": total_rows,
                "bad_quality_null_rows": bad_quality_null_rows,
                "bad_quality_non_null_violation_rows": bad_quality_non_null_violation_rows,
                "per_integ_class": class_counts,
                "xor17": str(xor17_acc),
                "xor53": str(xor53_acc),
                "min_ts_ms": min_ts_ms,
                "max_ts_ms": max_ts_ms,
            },
            "slices_1m": slice_summaries,
            "alarm_history": {
                "total_alarms": int(alarm_row[0]) if alarm_row else 0,
                "tagless_system_alarms": int(alarm_row[1]) if alarm_row else 0,
                "alarm_xor17": str(alarm_row[2]) if alarm_row else "0",
            },
            "consumer_metrics": {
                "duplicates_absorbed": duplicates_absorbed,
                "dedup_strategy": "In-memory sliding window (500k keys) + DB ON CONFLICT (site_id, tag_id, ts) DO UPDATE",
            },
        }
    finally:
        await conn.close()


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    custom_env = os.environ.get("EDGE_CONSUMER_ENV_FILE", "").strip()
    if custom_env:
        _load_env_file(Path(custom_env))
    _load_env_file(Path.cwd() / ".env")
    _load_env_file(project_root / ".env")

    parser = argparse.ArgumentParser(description="Read-only Upper VQT parity query tool (1-minute sliced XOR)")
    parser.add_argument("--site-id", type=str, default=None, help="Filter by site_id (e.g., edge-acceptance)")
    parser.add_argument("--start-ms", type=int, default=None, help="Inclusive start epoch ms")
    parser.add_argument("--end-ms", type=int, default=None, help="Inclusive end epoch ms")
    parser.add_argument("--slice-ms", type=int, default=60_000, help="Slice width in ms (default: 60000 = 1 minute)")
    parser.add_argument("--duplicates-absorbed", type=int, default=None, help="Optional consumer duplicates_absorbed counter")
    parser.add_argument(
        "--out",
        type=str,
        default=str(project_root / "prompts" / "upper_vqt_parity_result.json"),
        help="Output JSON file path",
    )
    args = parser.parse_args()

    dups = args.duplicates_absorbed
    if dups is None:
        dups = _read_consumer_duplicates_absorbed(project_root)

    dsn = os.getenv("TS_DSN", "postgresql://postgres:postgres@127.0.0.1:55432/postgres")
    result = asyncio.run(
        run_parity_query(
            dsn=dsn,
            site_id=args.site_id,
            start_ms=args.start_ms,
            end_ms=args.end_ms,
            duplicates_absorbed=dups,
            slice_ms=args.slice_ms,
        )
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
