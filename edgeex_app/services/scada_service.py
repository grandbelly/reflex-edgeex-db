"""Shared semantics for overview, process, trend, alarms and diagnostics."""
from datetime import datetime, timezone
import json
import math
from zoneinfo import ZoneInfo
from ..queries.scada import read_snapshot

QUALITY = {0: "BAD", 1: "UNCERTAIN", 2: "GOOD"}


def number(value):
    if value is None:
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def display(value):
    result = number(value)
    return "—" if result is None else format(result, ".8g")


def stamp(value):
    if value is None or value.tzinfo is None:
        return "—"
    return value.astimezone(ZoneInfo("Asia/Seoul")).isoformat(timespec="microseconds")


def freshness(observed, at, stale_after):
    if observed is None or observed.tzinfo is None:
        return "시각 확인 불가"
    age = (at - observed).total_seconds()
    if age < 0:
        return "시각 불일치"
    if stale_after is None:
        return "현재성 기준 미설정"
    return "오래된 표본" if age > stale_after else "최근 표본"


def shape_snapshot(raw, stale_after=None):
    if stale_after is not None and (not math.isfinite(stale_after) or stale_after <= 0):
        raise ValueError("stale_after must be finite and positive")
    site, at = raw["site_id"], raw["as_of"]
    rows = []
    for r in raw["latest"]:
        if r["site_id"] != site:
            raise ValueError("Cross-site sample rejected")
        q = r["final_quality"]
        known_quality = type(q) is int and q in QUALITY
        invalid_value = any(v is not None and number(v) is None
                            for v in (r["raw_val"], r["cond_val"], r["final_val"]))
        invalid_final = (q == 0 and r["final_val"] is not None) or (q in (1, 2) and r["final_val"] is None)
        # BAD never acquires a synthetic final value, even on malformed input.
        final = None if q == 0 else number(r["final_val"])
        rows.append(dict(
            site=site, tag=r["tag_id"], channel=r["channel"], unit=r["unit"],
            raw=display(r["raw_val"]), cond=display(r["cond_val"]), final=display(final),
            raw_value=number(r["raw_val"]), cond_value=number(r["cond_val"]), final_value=final,
            quality=QUALITY[q] if known_quality else "품질 미정의", observed_at=stamp(r["ts"]),
            validity="값 계약 오류" if not known_quality or invalid_value or invalid_final else "값 계약 일치",
            ingested_at=stamp(r["ingested_at"]),
            freshness=freshness(r["ts"], at, stale_after),
            reasons=json.dumps(r["reasons"], ensure_ascii=False) if not isinstance(r["reasons"], str)
                    else r["reasons"],
        ))
    series = []
    for r in raw["series"]:
        series.append(dict(time=stamp(r["ts"]), raw=number(r["raw_val"]),
                           cond=number(r["cond_val"]),
                           final=None if r["final_quality"] == 0 else number(r["final_val"]),
                           quality=QUALITY.get(r["final_quality"], "품질 미정의")))
    alarms = []
    alarm_section = raw["sections"]["alarms"]
    for r in alarm_section["rows"]:
        alarms.append(dict(event=str(r["event_id"]), time=stamp(r["triggered_at"]),
                           message=r["message"], level=str(r["level"]),
                           condition="복귀" if r["resolved"] else "발생",
                           acknowledgement="확인" if r["acknowledged"] else "미확인"))
    health = raw["sections"]["health"]
    health_rows = []
    for r in health["rows"]:
        try:
            body = r["payload"]
            if isinstance(body, str):
                body = json.loads(body)
            inner = body.get("payload", body)
            channels = inner.get("channels", {})
            if not isinstance(channels, dict):
                raise ValueError("channels must be an object")
        except (ValueError, TypeError, AttributeError):
            health = {**health, "state": "error", "code": "PAYLOAD_INVALID"}
            continue
        for channel, detail in channels.items():
            if not isinstance(detail, dict):
                continue
            state = detail.get("status")
            if state is None and isinstance(detail.get("ok"), bool):
                state = "ok" if detail["ok"] else "error"
            health_rows.append(dict(channel=channel, state=str(state) if state is not None else "—",
                                    time=stamp(r["ts"]),
                                    freshness=freshness(r["ts"], at, stale_after)))
    return {
        "site_id": site, "as_of": stamp(at), "served_at": stamp(raw["served_at"]),
        "selected_tag": raw["selected_tag"], "tags": [r["tag"] for r in rows],
        "rows": rows, "series": series, "alarms": alarms, "health_rows": health_rows,
        "health_state": "조회 실패 · " + health["code"] if health["state"] == "error" else
                        ("표본 없음" if not health["rows"] else "조회 성공 · 원천 시각 확인"),
        "alarm_state": "조회 실패 · " + alarm_section["code"] if alarm_section["state"] == "error"
                       else "최근 사건 최대 100건 · 전체 활성 경보 수와 다름",
        "counts": raw["counts"], "minutes": raw["minutes"],
        "series_truncated": raw["series_truncated"],
        "observed_tags": len(rows), "stale_tags": sum(r["freshness"] == "오래된 표본" for r in rows),
        "bad_tags": sum(r["quality"] == "BAD" for r in rows),
        "currentness_configured": stale_after is not None,
    }


class ScadaService:
    async def snapshot(self, site, tag="", minutes=15, stale_after=None):
        return shape_snapshot(await read_snapshot(site, tag, minutes), stale_after)
