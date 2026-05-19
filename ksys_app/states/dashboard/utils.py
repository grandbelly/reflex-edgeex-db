"""Dashboard utility functions — pure type conversions, formatting, statistics.

All functions extracted from states/dashboard.py during Stage 4 Sprint 3b.
Pure functions (no Reflex State, no DB). Reusable from other states.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def _to_float(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except Exception:  # noqa: BLE001
        return None


def _to_int(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except Exception:  # noqa: BLE001
        return None


def _fmt_s(v: Optional[float], digits: int) -> str:
    try:
        if v is None:
            return "0"
        return f"{float(v):.{digits}f}"
    except Exception:  # noqa: BLE001
        return "0"


def _fmt_s_int(v: Any) -> str:
    try:
        if v is None:
            return "0"
        return f"{int(v):d}"
    except Exception:  # noqa: BLE001
        return "0"


def _to_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    try:
        return str(v)
    except Exception:  # noqa: BLE001
        return None


def _norm_window(w: str) -> str:
    mapping = {
        # English labels (fine-grained)
        "1 min": "1 minutes",
        "5 min": "5 minutes",        
        "10 min": "10 minutes",
        "60 min": "60 minutes",
        "12 hour": "12 hours",
        "24 hour": "24 hours",
        "48 hour": "48 hours",
        "7 days": "7 days",
        "14 days": "14 days",
        "30 days": "30 days",
        "3 months": "90 days",
        "6 months": "180 days",
        "12 months": "365 days",
        # Backward-compat
        "5 minutes": "5 minutes",
        "15 minutes": "15 minutes",
        "1h": "1 hour",
        "1 hour": "1 hour",
        "6 hours": "6 hours",
        "12 hours": "12 hours",
        "4h": "4 hours",
        "4 hours": "4 hours",
        "24h": "24 hours",
        "24 hours": "24 hours",
        "7d": "7 days",
        "30d": "30 days",
    }
    return mapping.get(w, "24 hours")


SEOUL_TZ = ZoneInfo("Asia/Seoul")


def _fmt_ts_local(s: Optional[str]) -> str:
    if not s:
        return ""
    try:
        txt = str(s)
        if txt.endswith("Z"):
            txt = txt.replace("Z", "+00:00")
        dt = datetime.fromisoformat(txt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(SEOUL_TZ)
        z = local.strftime("%z")
        z = z[:3] + ":" + z[3:]
        return local.strftime("%Y-%m-%d %H:%M:%S") + z
    except Exception:  # noqa: BLE001
        return str(s)


def _fmt_ts_short(s: Optional[str]) -> str:
    if not s:
        return ""
    try:
        txt = str(s)
        if txt.endswith("Z"):
            txt = txt.replace("Z", "+00:00")
        dt = datetime.fromisoformat(txt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(SEOUL_TZ)
        return local.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        return str(s)

def _fmt_ts_time_only(s: Optional[str]) -> str:
    """시분초만 표시하는 타임스탬프 포매터"""
    if not s:
        return ""
    try:
        txt = str(s)
        if txt.endswith("Z"):
            txt = txt.replace("Z", "+00:00")
        dt = datetime.fromisoformat(txt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(SEOUL_TZ)
        return local.strftime("%H:%M:%S")  # 시분초만 표시
    except Exception:  # noqa: BLE001
        return str(s)[-8:] if len(str(s)) >= 8 else str(s)


def _fmt_ts_short_chart(s: Optional[str]) -> str:
    """차트 X축용 타임스탬프 포맷터 (년-월-일 시:분)"""
    if not s:
        return ""
    try:
        txt = str(s)
        if txt.endswith("Z"):
            txt = txt.replace("Z", "+00:00")
        dt = datetime.fromisoformat(txt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(SEOUL_TZ)
        return local.strftime("%Y-%m-%d %H:%M")  # 년-월-일 시:분 형식
    except Exception:  # noqa: BLE001
        return str(s)[:16] if len(str(s)) >= 16 else str(s)


def _mean_safe(values: List[Optional[float]]) -> Optional[float]:
    nums = [float(x) for x in values if isinstance(x, (int, float))]
    if not nums:
        return None
    return sum(nums) / float(len(nums))


def _stdev_safe(values: List[Optional[float]]) -> Optional[float]:
    nums = [float(x) for x in values if isinstance(x, (int, float))]
    n = len(nums)
    if n < 2:
        return None
    m = sum(nums) / n
    var = sum((x - m) ** 2 for x in nums) / (n - 1)
    return var ** 0.5


def _compute_indicators_fallback(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute SMA10/60, BB(20,2), slope_60 from series `avg` when DB indicators are missing.

    Expects rows sorted ASC by `bucket` and containing keys: bucket(str), tag_name(str), avg(float|None).
    """
    result: List[Dict[str, Any]] = []
    avg_series: List[Optional[float]] = [_to_float(r.get("avg")) for r in rows]
    for i, r in enumerate(rows):
        w10 = avg_series[max(0, i - 9) : i + 1]
        w20 = avg_series[max(0, i - 19) : i + 1]
        w60 = avg_series[max(0, i - 59) : i + 1]
        sma_10 = _mean_safe(w10)
        sma_60 = _mean_safe(w60)
        m20 = _mean_safe(w20)
        sd20 = _stdev_safe(w20)
        # Ensure BB values are reasonable (within 50% of mean)
        if m20 is not None and sd20 is not None:
            bb_top = m20 + 2 * sd20
            bb_bot = m20 - 2 * sd20
            # Sanity check: if BB bands are too wide (>50% from mean), use smaller multiplier
            if abs(bb_top - m20) > m20 * 0.5:
                bb_top = m20 + min(sd20, m20 * 0.1)
                bb_bot = m20 - min(sd20, m20 * 0.1)
        else:
            bb_top = None
            bb_bot = None
        slope_60 = None
        if i >= 60 and isinstance(avg_series[i], (int, float)) and isinstance(avg_series[i - 60], (int, float)):
            slope_60 = float(avg_series[i]) - float(avg_series[i - 60])
        result.append(
            {
                "bucket": r.get("bucket"),
                "tag_name": r.get("tag_name"),
                "avg": _to_float(r.get("avg")),
                "sma_10": sma_10,
                "sma_60": sma_60,
                "bb_top": bb_top,
                "bb_bot": bb_bot,
                "slope_60": slope_60,
            }
        )
    return result
