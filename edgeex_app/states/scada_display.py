"""Pure display shaping for the SCADA screens. Service output stays unchanged;
State adds `*_d` display keys from these helpers so views never format values."""
import json
import re

QUALITY_KO = {"GOOD": "양호", "UNCERTAIN": "불확실", "BAD": "불량"}
QUALITY_TONE = {"GOOD": "neutral", "UNCERTAIN": "uncertain", "BAD": "bad"}
EMPTY = {"", "—", "[]", "None", None}

# Layout model of assets/scada.css: workspace max 1600 px, 24 px padding, one 16 px gap
# between 12-fraction tracks, 1 px panel borders, and a 15 px page scrollbar.
WORKSPACE_MAX, WORKSPACE_PAD, GAP, BORDER, SCROLLBAR = 1600, 24, 16, 1, 15

# Every table: (key, label, min px, numeric). Numeric columns are right-aligned.
TABLES = {
    "channels": [("channel", "채널", 150, False), ("count_d", "관측 점", 76, True),
                 ("bad_d", "불량", 64, True)],
    "recent_alarms": [("time_d", "발생", 112, False), ("message_d", "내용", 220, False),
                      ("condition", "상태", 72, False)],
    "alarms": [("message_d", "사건", 240, False), ("level", "원천 우선순위", 96, False),
               ("time_d", "발생 시각", 112, False), ("condition", "발생/복귀", 80, False),
               ("acknowledgement", "확인", 64, False)],
    "points": [("tag", "태그 / 채널", 180, False), ("raw_d", "원시값", 96, True),
               ("cond_d", "처리값", 96, True), ("final_d", "최종값", 96, True),
               ("unit_d", "단위", 56, False), ("quality_d", "품질", 72, False),
               ("observed_d", "원천 시각", 112, False)],
    "health": [("channel", "채널", 150, False), ("state", "원천 상태", 96, False),
               ("time_d", "원천 시각", 112, False), ("freshness", "현재성", 96, False)],
    "channel_latest": [("channel", "채널", 150, False), ("count_d", "관측 점", 76, True),
                       ("latest_d", "최신 원천 시각", 112, False)],
}
# Where each table sits: share of the 12-fraction row (12 = full width).
PLACEMENT = {"channels": 4, "recent_alarms": 8, "alarms": 8, "points": 8, "health": 8,
             "channel_latest": 4}


def track_width(viewport: int, share: int) -> float:
    """Inner width of a panel spanning `share`/12 of a two-track row."""
    content = min(viewport - SCROLLBAR, WORKSPACE_MAX) - 2 * WORKSPACE_PAD
    if share == 12:
        return content - 2 * BORDER
    return (content - GAP) * share / 12 - 2 * BORDER


def table_min_width(name: str) -> int:
    return sum(width for _, _, width, _ in TABLES[name])


def overflow(name: str, viewport: int) -> float:
    """Pixels a table would scroll inside its panel; 0 means it fits."""
    return max(0.0, table_min_width(name) - track_width(viewport, PLACEMENT[name]))


def kst_short(value) -> str:
    """'2026-10-28T09:27:02.123456+09:00' -> '10-28 09:27:02'. Full ISO stays in the inspector."""
    m = re.match(r"\d{4}-(\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})", str(value or ""))
    return f"{m.group(1)} {m.group(2)}" if m else "—"


def group(text: str) -> str:
    """Thousands separators on the integer part; digits are never dropped."""
    if not re.fullmatch(r"-?\d+(\.\d+)?", text):
        return text  # '—', exponent notation, anything unexpected stays verbatim
    sign, body = ("-", text[1:]) if text.startswith("-") else ("", text)
    whole, _, frac = body.partition(".")
    return sign + f"{int(whole):,}" + ("." + frac if frac else "")


def align_decimals(values: list) -> list:
    """Pad one row's values to the same fractional digits. Pads, never rounds (DS-017 §11.32-7)."""
    texts = [str(v) for v in values]
    places = max((len(t.partition(".")[2]) for t in texts if re.fullmatch(r"-?\d+(\.\d+)?", t)),
                 default=0)
    out = []
    for t in texts:
        if re.fullmatch(r"-?\d+(\.\d+)?", t) and places:
            whole, _, frac = t.partition(".")
            t = f"{whole}.{frac.ljust(places, '0')}"
        out.append(group(t))
    return out


def reasons_text(value) -> str:
    """'["EWMA_APPLIED"]' -> 'EWMA_APPLIED'; empty list -> ''."""
    if value in EMPTY:
        return ""
    try:
        items = json.loads(value) if isinstance(value, str) else value
    except ValueError:
        return str(value)
    if isinstance(items, list):
        return ", ".join(str(i) for i in items)
    return str(items)


def ko_terms(text) -> str:
    """Source messages may carry English quality words; screens use DS-017 terms."""
    return re.sub(r"\b(GOOD|UNCERTAIN|BAD)\b", lambda m: QUALITY_KO[m.group(1)], str(text or ""))


def facts(row: dict, spec: list) -> list[list[str]]:
    """Label/value pairs with unknown values omitted, so no '—' rows are drawn."""
    return [[label, str(row.get(key))] for label, key in spec if row.get(key) not in EMPTY]


def point_row(r: dict) -> dict:
    raw, cond, final = align_decimals([r["raw"], r["cond"], r["final"]])
    q = r["quality"]
    return {**r, "raw_d": raw, "cond_d": cond, "final_d": final,
            "unit_d": r["unit"] if r.get("unit") not in EMPTY else "—",
            "quality_d": QUALITY_KO.get(q, q), "tone": QUALITY_TONE.get(q, "neutral"),
            "observed_d": kst_short(r["observed_at"]), "ingested_d": kst_short(r["ingested_at"]),
            "reasons_d": reasons_text(r["reasons"])}


def alarm_row(r: dict) -> dict:
    tone = {"1": "p1", "2": "p2", "3": "p3"}.get(r["level"], "neutral") \
        if r["condition"] == "발생" else "neutral"
    return {**r, "time_d": kst_short(r["time"]), "message_d": ko_terms(r["message"]), "tone": tone}


def sample_row(r: dict) -> dict:
    q = r["quality"]
    return {**r, "quality_d": QUALITY_KO.get(q, q), "tone": QUALITY_TONE.get(q, "neutral"),
            "reasons_d": reasons_text(r["reasons"])}


def health_message(state: str) -> str:
    """One factual line with cause and next step when the Health read failed."""
    if "SCHEMA_MISSING" in state:
        return "상위 DB에 Health 표 없음(설치 Consumer는 메모리 보관) — DDL 적용 뒤 표시"
    if "PAYLOAD_INVALID" in state:
        return "Health 기록 형식이 계약과 다릅니다 — 원천 payload를 확인하세요"
    if "조회 실패" in state:
        return "Health를 읽지 못했습니다(" + state.split("·")[-1].strip() + ") — 지금 조회를 누르세요"
    return ""
