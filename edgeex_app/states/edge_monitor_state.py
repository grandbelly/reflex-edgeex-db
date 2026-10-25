"""Reflex state for the EdgeEX Monitoring page (/edge-monitor).

Reads lossless VQT records (`public.edgeex_vqt_raw`), Edge alarms
(`public.alarm_history`), and Edge `/health` snapshots
(`public.edgeex_health_latest`) directly from TimescaleDB/PostgreSQL,
plus runtime consumer metrics from `logs/consumer_metrics.json`.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List

import plotly.graph_objects as go
import reflex as rx

from ..services.edge_monitor_service import EdgeMonitorService
from .base_state import BaseState

logger = logging.getLogger(__name__)


class EdgeMonitorState(BaseState):
    """State managing the EdgeEX monitoring dashboard (/edge-monitor)."""

    loading: bool = False
    auto_refresh: bool = True
    # Disabled by default so real Edge integration tests never mix simulator rows
    auto_simulate: bool = False
    kafka_worker_active: bool = False
    kafka_bootstrap: str = ""
    consumer_status: str = "DB Direct"
    last_updated: str = "-"

    # Top KPI summary vars
    active_site_id: str = "-"
    site_count: int = 0
    online_sites: int = 0
    tag_count: int = 0

    vqt_total_rows: int = 0
    good_quality_rows: int = 0
    uncertain_quality_rows: int = 0
    bad_quality_rows: int = 0
    bad_quality_null_rows: int = 0

    messages_processed: int = 0
    duplicates_absorbed: int = 0
    commits_succeeded: int = 0
    quality_ratio: float = 100.0
    protection_count: int = 0
    spike_suppressed: int = 0
    missing_held: int = 0
    stale_alarms: int = 0
    hunting_detected: int = 0
    collection_stopped: int = 0
    process_alarms: int = 0
    health_count: int = 0
    health_status: str = "WAITING"

    # Tables & lists
    sites: List[Dict[str, Any]] = []
    tag_rows: List[Dict[str, Any]] = []
    recent_feed: List[Dict[str, Any]] = []
    recent_alarms: List[Dict[str, Any]] = []
    available_tags: List[str] = []

    # Selected tag & chart series
    selected_tag: str = ""
    selected_series: List[Dict[str, Any]] = []

    @rx.var
    def tag_comparison_figure(self) -> go.Figure:
        """Build a Plotly chart comparing RAW vs COND vs FINAL values for the selected tag."""
        fig = go.Figure()

        if self.selected_series:
            xs = [pt.get("time", "") for pt in self.selected_series]
            raws = [pt.get("raw") for pt in self.selected_series]
            conds = [pt.get("cond") for pt in self.selected_series]
            finals = [pt.get("final") for pt in self.selected_series]

            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=raws,
                    mode="lines+markers",
                    name="RAW (원시 표본)",
                    line=dict(color="#ef4444", width=1.5, dash="dot"),
                    marker=dict(size=6, symbol="x"),
                    connectgaps=False,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=conds,
                    mode="lines",
                    name="COND (전처리 후)",
                    line=dict(color="#f59e0b", width=1.8, dash="dash"),
                    connectgaps=False,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=finals,
                    mode="lines+markers",
                    name="FINAL (확정 VQT · BAD=NULL)",
                    line=dict(color="#10b981", width=2.5),
                    marker=dict(size=6),
                    connectgaps=False,
                )
            )

            # Mark BAD (quality=0) timestamps on the chart
            bad_xs = [
                pt.get("time", "")
                for pt in self.selected_series
                if int(pt.get("quality", 2)) == 0
            ]
            if bad_xs:
                ref_vals = [
                    v for v in (finals + conds + raws) if isinstance(v, (int, float))
                ]
                y_mark = sum(ref_vals) / len(ref_vals) if ref_vals else 0.0
                fig.add_trace(
                    go.Scatter(
                        x=bad_xs,
                        y=[y_mark for _ in bad_xs],
                        mode="markers+text",
                        name="BAD (final_quality=0, NULL 보존)",
                        text=["BAD(NULL)" for _ in bad_xs],
                        textposition="top center",
                        marker=dict(color="#ef4444", size=11, symbol="diamond"),
                    )
                )

        fig.update_layout(
            margin=dict(l=40, r=20, t=28, b=36),
            height=290,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=11, color="#86868b"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
            xaxis=dict(
                showgrid=True,
                gridcolor="rgba(128,128,128,0.12)",
                tickfont=dict(size=10),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(128,128,128,0.12)",
                tickfont=dict(size=10),
            ),
            hovermode="x unified",
        )
        return fig

    @rx.event(background=True)
    async def initialize(self):
        """Initialize the Edge Monitoring page and start periodic DB polling."""
        async with self:
            self.loading = True
            self.kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
            in_app_consumer = (
                os.getenv("KAFKA_IN_APP_CONSUMER", "false").lower() == "true"
            )
            if in_app_consumer:
                try:
                    from ..services.kafka_consumer_worker import ensure_kafka_worker_started
                    self.kafka_worker_active = ensure_kafka_worker_started()
                except Exception as exc:
                    logger.warning("In-app Kafka worker skipped: %s", exc)
                    self.kafka_worker_active = False
            else:
                self.kafka_worker_active = False

        await self._refresh_snapshot()

        async with self:
            self.loading = False

        while True:
            await asyncio.sleep(3)
            async with self:
                if not self.auto_refresh:
                    break
            try:
                await self._refresh_snapshot()
            except Exception as exc:
                logger.error("EdgeMonitor refresh error: %s", exc)

    async def _refresh_snapshot(self):
        """Fetch latest VQT, Alarm, and Health data from DB and update state."""
        async with self:
            current_tag = self.selected_tag

        snap = await EdgeMonitorService.get_dashboard_snapshot(selected_tag=current_tag)

        async with self:
            self.active_site_id = snap.get("active_site_id", "-")
            self.site_count = snap.get("site_count", 0)
            self.online_sites = snap.get("online_sites", 0)
            self.tag_count = snap.get("tag_count", 0)

            self.vqt_total_rows = snap.get("vqt_total_rows", 0)
            self.good_quality_rows = snap.get("good_quality_rows", 0)
            self.uncertain_quality_rows = snap.get("uncertain_quality_rows", 0)
            self.bad_quality_rows = snap.get("bad_quality_rows", 0)
            self.bad_quality_null_rows = snap.get("bad_quality_null_rows", 0)

            self.messages_processed = snap.get("messages_processed", 0)
            self.duplicates_absorbed = snap.get("duplicates_absorbed", 0)
            self.commits_succeeded = snap.get("commits_succeeded", 0)
            self.quality_ratio = snap.get("quality_ratio", 100.0)
            self.protection_count = snap.get("protection_count", 0)
            self.spike_suppressed = snap.get("spike_suppressed", 0)
            self.missing_held = snap.get("missing_held", 0)
            self.stale_alarms = snap.get("stale_alarms", 0)
            self.hunting_detected = snap.get("hunting_detected", 0)
            self.collection_stopped = snap.get("collection_stopped", 0)
            self.process_alarms = snap.get("process_alarms", 0)
            self.health_count = snap.get("health_count", 0)
            self.health_status = snap.get("health_status", "WAITING")

            self.sites = snap.get("sites", [])
            self.tag_rows = snap.get("tag_rows", [])
            self.recent_feed = snap.get("recent_feed", [])
            self.recent_alarms = snap.get("recent_alarms", [])
            self.available_tags = snap.get("available_tags", [])
            self.selected_tag = snap.get("selected_tag", "")
            self.selected_series = snap.get("selected_series", [])
            self.last_updated = snap.get("last_updated", "-")
            self.consumer_status = (
                f"Active (commits={self.commits_succeeded})"
                if self.commits_succeeded > 0
                else ("DB Ready" if self.vqt_total_rows > 0 else "Waiting for Edge Messages")
            )

    @rx.event(background=True)
    async def refresh_now(self):
        """Manual refresh button handler."""
        await self._refresh_snapshot()

    @rx.event(background=True)
    async def select_tag(self, tag_id: str):
        """Select a tag to inspect its RAW/COND/FINAL series."""
        async with self:
            self.selected_tag = tag_id
        await self._refresh_snapshot()

    @rx.event
    def toggle_auto_refresh(self, value: bool):
        """Toggle 3-second DB polling."""
        self.auto_refresh = value
        if value:
            return EdgeMonitorState.initialize
