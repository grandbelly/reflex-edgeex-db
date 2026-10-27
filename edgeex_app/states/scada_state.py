"""One site/tag/time context for the six read-only migration routes."""
import asyncio
import os
from typing import Any
import reflex as rx
from .base_state import BaseState
from ._connection import client_connected
from ..services.scada_service import ScadaService


class ScadaState(BaseState):
    site_id: str = os.getenv("SCADA_SITE_ID", "")
    tag: str = os.getenv("SCADA_TAG_ID", "")
    minutes: str = "15"
    as_of: str = "—"
    served_at: str = "—"
    source_label: str = "edge_vqt · 읽기 전용"
    query_state: str = "조회 전"
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
    polling: bool = False
    live: bool = True
    _generation: int = 0
    _request: int = 0
    _reading: bool = False
    _pending: bool = False

    @rx.event(background=True)
    async def initialize(self):
        async with self:
            self._generation += 1
            generation = self._generation
            if not self.live:
                return
            self.polling = True
        while True:
            async with self:
                if generation != self._generation or not self.polling:
                    return
            if not client_connected(self):
                return
            await self._refresh()
            await asyncio.sleep(5)

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
                self.query_state = "조회 성공" if self.rows else "조회 성공 · 표본 없음"
                self.error_message = ""
        except Exception as exc:
            async with self:
                if request != self._request:
                    return
                code = getattr(exc, "code", None) or type(exc).__name__
                self.query_state = "조회 실패 · 이전 자료일 수 있음"
                self.error_message = "관제 조회 불가 · " + code
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
    async def change_site(self, value: str):
        async with self:
            self._request += 1
            self.site_id, self.tag = value.strip(), ""
            self.rows, self.series, self.tags, self.alarms, self.health_rows = [], [], [], [], []
            self.observed_tags = self.bad_tags = self.stale_tags = 0
            self.stale_label = "—"
            self.received = self.good = self.uncertain = self.bad = 0
            self.as_of = self.served_at = "—"
            self.query_state = self.health_state = self.alarm_state = "조회 전"
        await self._refresh()

    @rx.event(background=True)
    async def change_tag(self, value: str):
        async with self:
            self._request += 1
            self.tag = value
            self.series = []
        await self._refresh()

    @rx.event(background=True)
    async def change_minutes(self, value: str):
        async with self:
            self._request += 1
            self.minutes = value
        await self._refresh()

    @rx.event
    def stop(self):
        self.polling = False
        self._generation += 1
        self._request += 1
        self._pending = False

    @rx.event
    def toggle_live(self):
        self.live = not self.live
        if self.live:
            return ScadaState.initialize
        self.polling = False
        self._generation += 1
        self._request += 1
        self._pending = False
