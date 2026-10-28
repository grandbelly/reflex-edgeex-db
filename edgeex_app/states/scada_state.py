"""Shared, bounded read events. Browser timer owns polling lifetime."""
import asyncio
import os
from typing import Any, TypedDict
import reflex as rx
from ..services.scada_service import ScadaService
from . import scada_display as D


class ScopeForm(TypedDict):
    site: str
    tag: str
    minutes: str


class ScadaState(rx.State):
    site_id: str = os.getenv("SCADA_SITE_ID", "")
    tag: str = os.getenv("SCADA_TAG_ID", "")
    minutes: str = "15"
    as_of: str = "—"
    served_at: str = "—"
    query_state: str = "조회 전"
    error_message: str = ""
    health_state: str = "조회 전"
    alarm_state: str = "조회 전"
    tags: list[str] = []
    rows: list[dict[str, Any]] = []
    series: list[dict[str, Any]] = []
    alarms: list[dict[str, str]] = []
    health_rows: list[dict[str, str]] = []
    observed_tags: int = 0
    bad_tags: int = 0
    stale_tags: int = 0
    stale_label: str = "—"
    received: int = 0
    good: int = 0
    uncertain: int = 0
    bad: int = 0
    series_truncated: bool = False
    live: bool = True
    search: str = ""
    page: int = 0
    phase: str = "FINAL"
    sample_key: str = ""
    alarm_key: str = ""
    _request: int = 0
    _reading: bool = False
    _pending: bool = False

    @rx.var
    def filtered_rows(self) -> list[dict[str, Any]]:
        term = self.search.casefold().strip()
        return [r for r in self.rows if term in str(r["tag"]).casefold()
                or term in str(r["channel"]).casefold()]

    @rx.var
    def page_count(self) -> int:
        return max(1, (len(self.filtered_rows) + 11) // 12)

    @rx.var
    def visible_rows(self) -> list[dict[str, Any]]:
        start = min(self.page, self.page_count - 1) * 12
        return self.filtered_rows[start:start + 12]

    @rx.var
    def selected(self) -> dict[str, Any]:
        return next((r for r in self.rows if r["tag"] == self.tag), {
            k: "—" for k in ("tag", "channel", "raw", "cond", "final", "unit", "quality",
                              "validity", "freshness", "observed_at", "ingested_at", "reasons",
                              "raw_d", "cond_d", "final_d", "unit_d", "quality_d", "observed_d",
                              "ingested_d", "reasons_d")
        } | {"tone": "neutral"})

    @rx.var
    def selected_facts(self) -> list[list[str]]:
        return D.facts(self.selected, [("채널", "channel"), ("원시값", "raw_d"), ("처리값", "cond_d"),
                                       ("최종값", "final_d"), ("단위", "unit"), ("원천 시각", "observed_d"),
                                       ("적재 시각", "ingested_d"), ("현재성", "freshness"),
                                       ("처리 사유", "reasons_d")])

    @rx.var
    def as_of_d(self) -> str:
        return D.kst_short(self.as_of)

    @rx.var
    def health_note(self) -> str:
        return D.health_message(self.health_state)

    @rx.var
    def quality_mix(self) -> list[dict[str, Any]]:
        total = self.good + self.uncertain + self.bad
        return [{"label": label, "count_d": D.group(str(n)), "tone": tone,
                 "width": f"{100 * n / total:.2f}%" if total else "0%"}
                for label, n, tone in [("양호", self.good, "neutral"),
                                       ("불확실", self.uncertain, "uncertain"),
                                       ("불량", self.bad, "bad")]]

    @rx.var
    def attention_rows(self) -> list[dict[str, Any]]:
        result = []
        for row in self.rows:
            issue = ("값 계약 오류" if row["validity"] != "값 계약 일치" else
                     "품질 불량" if row["quality"] == "BAD" else
                     "갱신 지연" if row["freshness"] == "오래된 표본" else "")
            if issue:
                result.append({**row, "issue": issue,
                               "issue_tone": "uncertain" if issue == "갱신 지연" else "bad"})
        return result

    @rx.var
    def channel_rows(self) -> list[dict[str, Any]]:
        groups = {}
        for row in self.rows:
            key = row["channel"]
            group = groups.setdefault(key, {"channel": key, "count": 0, "bad": 0, "latest": "—"})
            group["count"] += 1
            group["bad"] += int(row["quality"] == "BAD")
            if group["latest"] == "—" or row["observed_at"] > group["latest"]:
                group["latest"] = row["observed_at"]
        return [{**g, "count_d": D.group(str(g["count"])), "bad_d": D.group(str(g["bad"])),
                 "latest_d": D.kst_short(g["latest"])} for g in groups.values()]

    @rx.var
    def inspected_sample(self) -> dict[str, Any]:
        if self.series:
            return next((r for r in self.series if r["sample_key"] == self.sample_key), self.series[-1])
        return {**{k: "—" for k in ["time", "ingested_at", "raw_display", "cond_display",
                                    "final_display", "reasons", "reasons_d", "quality", "quality_d",
                                    "sample_key"]}, "epoch_ms": 0, "tone": "neutral"}

    @rx.var
    def sample_facts(self) -> list[list[str]]:
        return D.facts(self.inspected_sample, [("원천 시각", "time"), ("적재 시각", "ingested_at"),
                                               ("원시값", "raw_display"), ("처리값", "cond_display"),
                                               ("최종값", "final_display"), ("처리 사유", "reasons_d")])

    @rx.var
    def sample_position(self) -> int:
        return next((i for i, r in enumerate(self.series) if r["sample_key"] == self.sample_key),
                    max(0, len(self.series) - 1))

    @rx.var
    def sample_max(self) -> int:
        return max(1, len(self.series) - 1)

    @rx.var
    def cursor_time(self) -> int:
        # Recharts ReferenceLine accepts integer milliseconds; precise source ISO stays in the inspector.
        return round(float(self.inspected_sample["epoch_ms"]))

    @rx.var
    def selected_alarm(self) -> dict[str, str]:
        return next((r for r in self.alarms if r["event"] == self.alarm_key),
                    self.alarms[0] if self.alarms else {k: "—" for k in
                    ["event", "time", "time_d", "message", "message_d", "level", "condition",
                     "acknowledgement"]} | {"tone": "neutral"})

    @rx.var
    def alarm_facts(self) -> list[list[str]]:
        return D.facts(self.selected_alarm, [("사건 ID", "event"), ("발생 시각", "time"),
                                             ("원천 우선순위", "level"), ("원천 상태", "condition"),
                                             ("확인", "acknowledgement")])

    @rx.var
    def recent_alarms(self) -> list[dict[str, str]]:
        return self.alarms[:5]

    @rx.event
    def inspect_sample(self, positions: list[int | float]):
        if positions and self.series:
            index = max(0, min(int(positions[0]), len(self.series) - 1))
            self.sample_key = self.series[index]["sample_key"]

    @rx.event
    def select_alarm(self, key: str):
        if any(row["event"] == key for row in self.alarms):
            self.alarm_key = key

    @rx.event
    def set_phase(self, phase: str | list[str]):
        if isinstance(phase, list):
            phase = phase[0] if phase else ""
        if phase in {"FINAL", "비교"}:
            self.phase = phase

    @rx.event(background=True)
    async def change_window(self, minutes: str):
        if minutes not in {"5", "15", "60"}:
            return
        async with self:
            self._request += 1
            self.minutes, self.series, self.sample_key = minutes, [], ""
        await self._refresh()

    @rx.event(background=True)
    async def initialize(self):
        async with self:
            live, empty = self.live, self.as_of == "—"
        if live or empty:
            await self._refresh()

    @rx.event(background=True)
    async def poll_tick(self):
        async with self:
            live = self.live
        if live:
            await self._refresh()

    async def _refresh(self):
        async with self:
            if self._reading:
                self._pending = True
                return
            self._reading = True
            self.query_state = "조회 중"
            self._request += 1
            request = self._request
            site, tag, minutes = self.site_id, self.tag, self.minutes
        try:
            limit = os.getenv("SCADA_STALE_AFTER_S")
            snapshot = await asyncio.wait_for(
                ScadaService().snapshot(site, tag, int(minutes), float(limit) if limit else None), 8,
            )
            async with self:
                if request != self._request or (site, tag, minutes) != (self.site_id, self.tag, self.minutes):
                    return
                self.as_of, self.served_at = snapshot["as_of"], snapshot["served_at"]
                self.tags, self.tag = snapshot["tags"], snapshot["selected_tag"]
                self.rows = [D.point_row(r) for r in snapshot["rows"]]
                self.series = [D.sample_row(r) for r in snapshot["series"]]
                self.alarms = [D.alarm_row(r) for r in snapshot["alarms"]]
                self.health_rows = [{**r, "time_d": D.kst_short(r["time"])} for r in snapshot["health_rows"]]
                self.health_state, self.alarm_state = snapshot["health_state"], snapshot["alarm_state"]
                self.observed_tags, self.stale_tags = snapshot["observed_tags"], snapshot["stale_tags"]
                self.bad_tags = snapshot["bad_tags"]
                self.stale_label = str(self.stale_tags) if snapshot["currentness_configured"] else "—"
                self.series_truncated = snapshot["series_truncated"]
                for field in ("received", "good", "uncertain", "bad"):
                    setattr(self, field, int(snapshot["counts"][field]))
                self.page = min(self.page, self.page_count - 1)
                self.query_state = "조회 완료" if self.rows else "표본 없음"
                self.error_message = ""
        except Exception as exc:
            async with self:
                if request != self._request:
                    return
                code = getattr(exc, "code", None) or type(exc).__name__
                self.query_state = "조회 실패"
                self.error_message = "새 자료를 읽지 못했습니다. 마지막 조회 시각을 확인하세요. · " + code
        finally:
            async with self:
                self._reading = False
                pending, self._pending = self._pending, False
            if pending:
                await self._refresh()

    @rx.event(background=True)
    async def refresh_now(self):
        await self._refresh()

    @rx.event(background=True)
    async def apply_scope(self, form_data: ScopeForm):
        site, tag, minutes = form_data["site"].strip(), form_data["tag"], form_data["minutes"]
        if not site or len(site) > 200 or len(tag) > 300 or minutes not in {"5", "15", "60"}:
            async with self:
                self.error_message = "현장 ID와 조회 기간을 확인하세요."
            return
        async with self:
            self._request += 1
            if site != self.site_id:
                tag = ""
            self.site_id, self.tag, self.minutes = site, tag, minutes
            self.rows, self.series, self.tags, self.alarms, self.health_rows = [], [], [], [], []
            self.observed_tags = self.bad_tags = self.stale_tags = 0
            self.stale_label = "—"
            self.received = self.good = self.uncertain = self.bad = 0
            self.as_of = self.served_at = "—"
            self.query_state = self.health_state = self.alarm_state = "조회 중"
            self.page = 0
        await self._refresh()

    @rx.event(background=True)
    async def select_tag(self, value: str):
        async with self:
            if value not in self.tags:
                return
            self._request += 1
            self.tag, self.series = value, []
            live = self.live
        if live:
            await self._refresh()

    @rx.event
    def change_search(self, value: str):
        self.search, self.page = value, 0

    @rx.event
    def previous_page(self):
        self.page = max(0, self.page - 1)

    @rx.event
    def next_page(self):
        self.page = min(self.page_count - 1, self.page + 1)

    @rx.event
    def toggle_live(self):
        self.live = not self.live
        if self.live:
            return ScadaState.refresh_now
        self._request += 1
        self._pending = False
