"""Shared, bounded read events. Browser timer owns polling lifetime."""
import asyncio
import os
from typing import Any, TypedDict
import reflex as rx
from ..services.scada_service import ScadaService


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
                              "validity", "freshness", "observed_at", "ingested_at", "reasons")
        })

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
                self.rows, self.series = snapshot["rows"], snapshot["series"]
                self.alarms, self.health_rows = snapshot["alarms"], snapshot["health_rows"]
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
