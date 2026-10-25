"""Presentation view for the EdgeEX Monitoring page (/edge-monitor).

Renders deterministic DOM sections and data tables backed by:
  - `public.edgeex_vqt_raw` (lossless VQT history including `final_quality=0` NULL rows)
  - `public.alarm_history` (Edge alarm events)
  - `public.edgeex_health_latest` (Edge `/health` status snapshots)
"""
from __future__ import annotations

from typing import Any, Dict
import reflex as rx

from ..design_system import am
from ..states.edge_monitor_state import EdgeMonitorState


def _quality_badge(quality_label: rx.Var) -> rx.Component:
    """Render a semantic quality pill for GOOD (2), UNCERTAIN (1), or BAD (0)."""
    return rx.match(
        quality_label,
        ("GOOD (2)", am.status_pill("GOOD (2)", tone="success")),
        ("UNCERTAIN (1)", am.status_pill("UNCERTAIN (1)", tone="warning")),
        ("BAD (0)", am.status_pill("BAD (0)", tone="error")),
        am.status_pill(quality_label, tone="info"),
    )


def _integ_badge(integ_state: rx.Var) -> rx.Component:
    """Render an integration state pill."""
    return rx.match(
        integ_state,
        ("NORMAL", am.status_pill("NORMAL", tone="success")),
        ("HOLDING", am.status_pill("HOLDING (LOCF)", tone="warning")),
        ("STOPPED", am.status_pill("STOPPED (BAD)", tone="error")),
        ("CALIBRATING", am.status_pill("CALIBRATING", tone="info")),
        ("DEMOTED", am.status_pill("DEMOTED", tone="warning")),
        am.status_pill(integ_state, tone="muted"),
    )


def _health_row_card(site: Dict[str, Any]) -> rx.Component:
    """Render a single Edge `/health` site status row."""
    tone = rx.match(
        site["status_tone"],
        ("success", "success"),
        ("warning", "warning"),
        ("error", "error"),
        "info",
    )
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("server", size=16, color=am.ACCENT),
                rx.el.span(
                    site["site_id"],
                    class_name="edge-health-site-id",
                    style={
                        "fontSize": "14px",
                        "fontWeight": "700",
                        "color": am.TEXT,
                        "fontFamily": am.FONT_MONO,
                    },
                ),
                am.status_pill(site["status"], tone=tone),
                rx.el.span(
                    f"Liveness: {site['liveness']}",
                    class_name="edge-health-liveness",
                    style={"fontSize": "12px", "color": am.MUTED, "fontFamily": am.FONT_MONO},
                ),
                style={"display": "flex", "alignItems": "center", "gap": "10px", "flexWrap": "wrap"},
            ),
            rx.el.div(
                rx.el.span(
                    f"ts_ms: {site['ts_ms']}",
                    class_name="edge-health-ts-ms",
                    style={"fontSize": "12px", "color": am.MUTED, "fontFamily": am.FONT_MONO},
                ),
                rx.el.span(
                    f"수신: {site['updated_at']}",
                    style={"fontSize": "12px", "color": am.MUTED_2, "fontFamily": am.FONT_MONO},
                ),
                style={"display": "flex", "alignItems": "center", "gap": "14px"},
            ),
            style={
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "flexWrap": "wrap",
                "gap": "8px",
            },
        ),
        rx.el.div(
            site["summary"],
            class_name="edge-health-summary",
            style={
                "fontSize": "12px",
                "color": am.MUTED,
                "fontFamily": am.FONT_MONO,
                "marginTop": "6px",
            },
        ),
        class_name="edge-health-item",
        style={
            "background": am.ROW,
            "border": f"1px solid {am.BORDER}",
            "borderRadius": am.R_LG,
            "padding": "12px 16px",
        },
    )


def _tag_latest_tr(row: Dict[str, Any]) -> rx.Component:
    """Render a row in the Tag Latest VQT Snapshot table."""
    is_selected = EdgeMonitorState.selected_tag == row["tag_id"]
    is_bad = row["quality"] == 0
    return rx.el.tr(
        rx.el.td(
            rx.el.span(
                row["tag_id"],
                class_name="edge-latest-tag-id",
                style={
                    "fontFamily": am.FONT_MONO,
                    "fontWeight": "700",
                    "color": am.ACCENT,
                },
            ),
            style={"padding": "10px 12px"},
        ),
        rx.el.td(
            row["site_id"],
            style={"padding": "10px 12px", "fontSize": "12px", "color": am.MUTED, "fontFamily": am.FONT_MONO},
        ),
        rx.el.td(
            row["time"],
            style={"padding": "10px 12px", "fontSize": "12px", "color": am.MUTED, "fontFamily": am.FONT_MONO},
        ),
        rx.el.td(
            row["ts_ms"].to_string(),
            style={"padding": "10px 12px", "fontSize": "12px", "color": am.MUTED_2, "fontFamily": am.FONT_MONO},
        ),
        rx.el.td(
            row["raw_str"],
            style={
                "padding": "10px 12px",
                "textAlign": "right",
                "fontFamily": am.FONT_MONO,
                "fontSize": "12px",
                "color": am.MUTED,
            },
        ),
        rx.el.td(
            row["cond_str"],
            style={
                "padding": "10px 12px",
                "textAlign": "right",
                "fontFamily": am.FONT_MONO,
                "fontSize": "12px",
                "color": am.TEXT,
            },
        ),
        rx.el.td(
            rx.el.span(
                row["final_str"],
                class_name="edge-latest-final-val",
                style={
                    "fontFamily": am.FONT_MONO,
                    "fontSize": "13px",
                    "fontWeight": "700",
                    "color": rx.cond(is_bad, am.ERROR, am.TEXT),
                },
            ),
            style={"padding": "10px 12px", "textAlign": "right"},
        ),
        rx.el.td(
            _quality_badge(row["quality_label"]),
            class_name="edge-latest-quality",
            style={"padding": "10px 12px", "textAlign": "center"},
        ),
        rx.el.td(
            _integ_badge(row["integ_state"]),
            style={"padding": "10px 12px", "textAlign": "center"},
        ),
        rx.el.td(
            rx.el.span(
                row["reasons_str"],
                style={
                    "fontFamily": am.FONT_MONO,
                    "fontSize": "11px",
                    "color": rx.cond(row["reasons_str"] == "정상 (0x0)", am.MUTED, am.WARNING),
                },
            ),
            style={"padding": "10px 12px"},
        ),
        on_click=EdgeMonitorState.select_tag(row["tag_id"]),
        class_name="edge-latest-row",
        style={
            "borderBottom": f"1px solid {am.HAIRLINE}",
            "background": rx.cond(is_selected, "rgba(0, 102, 204, 0.08)", "transparent"),
            "cursor": "pointer",
        },
    )


def _vqt_history_tr(item: Dict[str, Any]) -> rx.Component:
    """Render a row in the VQT Lossless History table (`edgeex_vqt_raw`)."""
    is_bad = item["quality"] == 0
    return rx.el.tr(
        rx.el.td(
            item["time"],
            style={"padding": "8px 10px", "fontSize": "12px", "fontFamily": am.FONT_MONO, "color": am.MUTED},
        ),
        rx.el.td(
            item["ts_ms"].to_string(),
            class_name="edge-vqt-ts-ms",
            style={"padding": "8px 10px", "fontSize": "12px", "fontFamily": am.FONT_MONO, "color": am.MUTED_2},
        ),
        rx.el.td(
            item["site_id"],
            style={"padding": "8px 10px", "fontSize": "12px", "fontFamily": am.FONT_MONO, "color": am.MUTED},
        ),
        rx.el.td(
            rx.el.span(
                item["tag_id"],
                class_name="edge-vqt-tag-id",
                style={"fontSize": "12px", "fontFamily": am.FONT_MONO, "fontWeight": "600", "color": am.TEXT},
            ),
            style={"padding": "8px 10px"},
        ),
        rx.el.td(
            item["raw_str"],
            style={"padding": "8px 10px", "textAlign": "right", "fontSize": "12px", "fontFamily": am.FONT_MONO, "color": am.MUTED},
        ),
        rx.el.td(
            item["cond_str"],
            style={"padding": "8px 10px", "textAlign": "right", "fontSize": "12px", "fontFamily": am.FONT_MONO, "color": am.TEXT},
        ),
        rx.el.td(
            rx.el.span(
                item["final_str"],
                class_name="edge-vqt-final-val",
                style={
                    "fontSize": "12px",
                    "fontFamily": am.FONT_MONO,
                    "fontWeight": "700",
                    "color": rx.cond(is_bad, am.ERROR, am.TEXT),
                },
            ),
            style={"padding": "8px 10px", "textAlign": "right"},
        ),
        rx.el.td(
            _quality_badge(item["quality_label"]),
            class_name="edge-vqt-quality",
            style={"padding": "8px 10px", "textAlign": "center"},
        ),
        rx.el.td(
            _integ_badge(item["integ_state"]),
            style={"padding": "8px 10px", "textAlign": "center"},
        ),
        rx.el.td(
            rx.el.span(
                item["reasons_str"],
                style={"fontSize": "11px", "fontFamily": am.FONT_MONO, "color": am.MUTED},
            ),
            style={"padding": "8px 10px"},
        ),
        class_name="edge-vqt-row",
        style={
            "borderBottom": f"1px solid {am.HAIRLINE}",
            "background": rx.cond(is_bad, "rgba(239, 68, 68, 0.06)", "transparent"),
        },
    )


def _alarm_tr(alarm: Dict[str, Any]) -> rx.Component:
    """Render an Edge alarm row from `public.alarm_history`."""
    tone = rx.match(
        alarm["level_tone"],
        ("error", "error"),
        ("warning", "warning"),
        "info",
    )
    return rx.el.tr(
        rx.el.td(
            alarm["time"],
            style={"padding": "10px 12px", "fontSize": "12px", "fontFamily": am.FONT_MONO, "color": am.MUTED},
        ),
        rx.el.td(
            rx.el.span(
                alarm["event_id"],
                class_name="edge-alarm-event-id",
                style={"fontSize": "12px", "fontFamily": am.FONT_MONO, "color": am.MUTED_2},
            ),
            style={"padding": "10px 12px"},
        ),
        rx.el.td(
            rx.el.span(
                alarm["tag_id"],
                class_name="edge-alarm-tag-id",
                style={"fontSize": "12px", "fontFamily": am.FONT_MONO, "fontWeight": "700", "color": am.TEXT},
            ),
            style={"padding": "10px 12px"},
        ),
        rx.el.td(
            am.status_pill(alarm["level_name"], tone=tone),
            class_name="edge-alarm-level",
            style={"padding": "10px 12px", "textAlign": "center"},
        ),
        rx.el.td(
            rx.el.span(
                alarm["message"],
                class_name="edge-alarm-message",
                style={"fontSize": "13px", "fontWeight": "600", "color": am.TEXT},
            ),
            style={"padding": "10px 12px"},
        ),
        rx.el.td(
            rx.el.span(
                alarm["cause"],
                class_name="edge-alarm-cause",
                style={"fontSize": "12px", "fontFamily": am.FONT_MONO, "color": am.MUTED},
            ),
            style={"padding": "10px 12px"},
        ),
        rx.el.td(
            am.status_pill(
                alarm["resolved_label"],
                tone=rx.cond(alarm["resolved"], "success", "error"),
            ),
            style={"padding": "10px 12px", "textAlign": "center"},
        ),
        class_name="edge-alarm-row",
        style={"borderBottom": f"1px solid {am.HAIRLINE}"},
    )


def edge_monitor_view() -> rx.Component:
    """Main view for the /edge-monitor page."""
    return am.page_container(
        # ── Header bar ──
        am.header_bar(
            title="Edge 관제 (Kafka VQT · 경보 · Health)",
            subtitle="edgeex_vqt_raw (무손실 VQT · BAD NULL 보존) · alarm_history · edgeex_health_latest 실시간 조회",
            badge=am.status_pill(
                f"Consumer: {EdgeMonitorState.consumer_status} · {EdgeMonitorState.last_updated}",
                tone="success",
            ),
            actions=rx.el.div(
                rx.el.label(
                    rx.switch(
                        checked=EdgeMonitorState.auto_refresh,
                        on_change=EdgeMonitorState.toggle_auto_refresh,
                        size="1",
                    ),
                    rx.el.span("3초 자동 갱신", style={"fontSize": "12px", "color": am.MUTED}),
                    style={"display": "flex", "alignItems": "center", "gap": "6px"},
                ),
                am.pill_button(
                    "즉시 새로고침",
                    on_click=EdgeMonitorState.refresh_now,
                    variant="primary",
                    icon="refresh-cw",
                ),
                style={"display": "flex", "alignItems": "center", "gap": "10px", "flexWrap": "wrap"},
            ),
        ),
        # ── Top KPI Grid (5 cards) ──
        rx.el.div(
            rx.el.div(
                am.kpi_tile(
                    label="연결된 Edge 사이트",
                    value=EdgeMonitorState.site_count.to_string(),
                    unit="개소",
                    delta=f"Health: {EdgeMonitorState.health_status}",
                    delta_tone="success",
                    subtitle=f"Site: {EdgeMonitorState.active_site_id} · 태그 {EdgeMonitorState.tag_count}종",
                    icon="server",
                ),
                id="kpi-edge-site",
            ),
            rx.el.div(
                am.kpi_tile(
                    label="적재된 VQT 표본 (edgeex_vqt_raw)",
                    value=EdgeMonitorState.vqt_total_rows.to_string(),
                    unit="행",
                    delta=f"BAD(품질0): {EdgeMonitorState.bad_quality_null_rows}건 NULL 보존",
                    delta_tone=rx.cond(EdgeMonitorState.bad_quality_rows > 0, "warning", "info"),
                    subtitle=(
                        f"GOOD {EdgeMonitorState.good_quality_rows} · "
                        f"UNCERTAIN {EdgeMonitorState.uncertain_quality_rows} · "
                        f"중복흡수 {EdgeMonitorState.duplicates_absorbed}"
                    ),
                    icon="database",
                ),
                id="kpi-vqt-total",
            ),
            rx.el.div(
                am.kpi_tile(
                    label="VQT 유효 품질율 (GOOD)",
                    value=EdgeMonitorState.quality_ratio.to_string(),
                    unit="%",
                    delta=f"BAD {EdgeMonitorState.bad_quality_rows}건",
                    delta_tone=rx.cond(EdgeMonitorState.bad_quality_rows > 0, "warning", "success"),
                    subtitle=f"GOOD {EdgeMonitorState.good_quality_rows} / 전체 {EdgeMonitorState.vqt_total_rows}행",
                    icon="shield-check",
                ),
                id="kpi-vqt-quality",
            ),
            rx.el.div(
                am.kpi_tile(
                    label="전처리 이상치·결측 방어",
                    value=EdgeMonitorState.protection_count.to_string(),
                    unit="건",
                    delta=f"Spike {EdgeMonitorState.spike_suppressed} / LOCF {EdgeMonitorState.missing_held}",
                    delta_tone="warning",
                    subtitle=(
                        f"STALE {EdgeMonitorState.stale_alarms} · "
                        f"HUNT {EdgeMonitorState.hunting_detected} · "
                        f"STOP {EdgeMonitorState.collection_stopped}"
                    ),
                    icon="filter",
                ),
                id="kpi-edge-protection",
            ),
            rx.el.div(
                am.kpi_tile(
                    label="경보 및 Health 수신",
                    value=EdgeMonitorState.process_alarms.to_string(),
                    unit="건",
                    delta=f"Health {EdgeMonitorState.health_count}건 ({EdgeMonitorState.health_status})",
                    delta_tone=rx.cond(EdgeMonitorState.process_alarms > 0, "error", "success"),
                    subtitle="alarm_history · edgeex_health_latest",
                    icon="bell",
                ),
                id="kpi-alarm-health",
            ),
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fit, minmax(220px, 1fr))",
                "gap": "16px",
                "marginBottom": "20px",
            },
        ),
        # ── Section 1: Edge /health Status Snapshot ──
        rx.el.div(
            am.card(
                am.section_header(
                    "엣지 /health 상태 스냅샷 (edgeex_health_latest)",
                    subtitle="health 토픽 수신 최신 상태 · site_id 별 1행 유지",
                    right=am.status_pill(
                        f"수신 사이트: {EdgeMonitorState.health_count}건",
                        tone="info",
                    ),
                ),
                rx.cond(
                    EdgeMonitorState.sites.length() > 0,
                    rx.el.div(
                        rx.foreach(EdgeMonitorState.sites, _health_row_card),
                        style={"display": "flex", "flexDirection": "column", "gap": "10px"},
                    ),
                    rx.el.div(
                        "수신된 /health 메시지가 없습니다.",
                        id="edge-health-empty",
                        style={"padding": "16px", "color": am.MUTED, "fontSize": "13px"},
                    ),
                ),
                style={"marginBottom": "20px"},
            ),
            id="section-health-status",
        ),
        # ── Section 2: Tag Latest VQT Snapshot Table ──
        rx.el.div(
            am.card(
                am.section_header(
                    "태그별 최신 VQT 스냅샷 (DISTINCT ON tag_id)",
                    subtitle="각 태그의 가장 최근 ts_ms 표본 · final_quality=0(BAD)인 경우 FINAL 값은 NULL (BAD 보존)으로 표시",
                    right=am.status_pill(
                        f"태그 수: {EdgeMonitorState.tag_count}종",
                        tone="info",
                    ),
                ),
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("태그 ID", style={"padding": "10px 12px", "textAlign": "left"}),
                                rx.el.th("사이트", style={"padding": "10px 12px", "textAlign": "left"}),
                                rx.el.th("수집 시각 (UTC)", style={"padding": "10px 12px", "textAlign": "left"}),
                                rx.el.th("ts_ms", style={"padding": "10px 12px", "textAlign": "left"}),
                                rx.el.th("RAW", style={"padding": "10px 12px", "textAlign": "right"}),
                                rx.el.th("COND", style={"padding": "10px 12px", "textAlign": "right"}),
                                rx.el.th("FINAL (최종값)", style={"padding": "10px 12px", "textAlign": "right"}),
                                rx.el.th("품질 (Quality)", style={"padding": "10px 12px", "textAlign": "center"}),
                                rx.el.th("INTEG 상태", style={"padding": "10px 12px", "textAlign": "center"}),
                                rx.el.th("사유 비트 (reasons)", style={"padding": "10px 12px", "textAlign": "left"}),
                                style={
                                    "borderBottom": f"1px solid {am.BORDER}",
                                    "fontSize": "11px",
                                    "fontWeight": "600",
                                    "color": am.MUTED,
                                    "textTransform": "uppercase",
                                },
                            )
                        ),
                        rx.el.tbody(
                            rx.foreach(EdgeMonitorState.tag_rows, _tag_latest_tr),
                            id="tbody-tag-latest",
                        ),
                        id="table-tag-latest",
                        style={"width": "100%", "borderCollapse": "collapse"},
                    ),
                    style={"overflowX": "auto"},
                ),
                style={"marginBottom": "20px"},
            ),
            id="section-tag-latest",
        ),
        # ── Section 3: Lossless VQT Raw History Table (All recent rows) ──
        rx.el.div(
            am.card(
                am.section_header(
                    "VQT 무손실 적재 이력 (edgeex_vqt_raw 전수 조회)",
                    subtitle="정상(GOOD=2)·불확실(UNCERTAIN=1)·불량(BAD=0, final_val=NULL) 전 표본 무손실 보존",
                    right=am.status_pill(
                        f"전체 적재: {EdgeMonitorState.vqt_total_rows}행 (BAD: {EdgeMonitorState.bad_quality_rows}행)",
                        tone=rx.cond(EdgeMonitorState.bad_quality_rows > 0, "warning", "success"),
                    ),
                ),
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("수집 시각 (UTC)", style={"padding": "8px 10px", "textAlign": "left"}),
                                rx.el.th("ts_ms", style={"padding": "8px 10px", "textAlign": "left"}),
                                rx.el.th("사이트", style={"padding": "8px 10px", "textAlign": "left"}),
                                rx.el.th("태그 ID", style={"padding": "8px 10px", "textAlign": "left"}),
                                rx.el.th("RAW", style={"padding": "8px 10px", "textAlign": "right"}),
                                rx.el.th("COND", style={"padding": "8px 10px", "textAlign": "right"}),
                                rx.el.th("FINAL (최종값)", style={"padding": "8px 10px", "textAlign": "right"}),
                                rx.el.th("품질 (Quality)", style={"padding": "8px 10px", "textAlign": "center"}),
                                rx.el.th("INTEG 상태", style={"padding": "8px 10px", "textAlign": "center"}),
                                rx.el.th("사유 비트 (reasons)", style={"padding": "8px 10px", "textAlign": "left"}),
                                style={
                                    "borderBottom": f"1px solid {am.BORDER}",
                                    "fontSize": "11px",
                                    "fontWeight": "600",
                                    "color": am.MUTED,
                                    "textTransform": "uppercase",
                                },
                            )
                        ),
                        rx.el.tbody(
                            rx.foreach(EdgeMonitorState.recent_feed, _vqt_history_tr),
                            id="tbody-vqt-history",
                        ),
                        id="table-vqt-history",
                        style={"width": "100%", "borderCollapse": "collapse"},
                    ),
                    style={"overflowX": "auto", "maxHeight": "420px", "overflowY": "auto"},
                ),
                style={"marginBottom": "20px"},
            ),
            id="section-vqt-all-rows",
        ),
        # ── Section 4: Edge Alarms Table (`alarm_history`) ──
        rx.el.div(
            am.card(
                am.section_header(
                    "엣지 경보 수신 이력 (alarm_history)",
                    subtitle="alarms 토픽에서 수신·적재된 공정 및 통신/수집 경보",
                    right=am.status_pill(
                        f"경보 건수: {EdgeMonitorState.process_alarms}건",
                        tone=rx.cond(EdgeMonitorState.process_alarms > 0, "error", "success"),
                    ),
                ),
                rx.cond(
                    EdgeMonitorState.recent_alarms.length() > 0,
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    rx.el.th("발생 시각 (UTC)", style={"padding": "10px 12px", "textAlign": "left"}),
                                    rx.el.th("event_id", style={"padding": "10px 12px", "textAlign": "left"}),
                                    rx.el.th("태그 ID", style={"padding": "10px 12px", "textAlign": "left"}),
                                    rx.el.th("등급 (Level)", style={"padding": "10px 12px", "textAlign": "center"}),
                                    rx.el.th("경보 메시지", style={"padding": "10px 12px", "textAlign": "left"}),
                                    rx.el.th("원인 · 상태", style={"padding": "10px 12px", "textAlign": "left"}),
                                    rx.el.th("해제 여부", style={"padding": "10px 12px", "textAlign": "center"}),
                                    style={
                                        "borderBottom": f"1px solid {am.BORDER}",
                                        "fontSize": "11px",
                                        "fontWeight": "600",
                                        "color": am.MUTED,
                                        "textTransform": "uppercase",
                                    },
                                )
                            ),
                            rx.el.tbody(
                                rx.foreach(EdgeMonitorState.recent_alarms, _alarm_tr),
                                id="tbody-edge-alarms",
                            ),
                            id="table-edge-alarms",
                            style={"width": "100%", "borderCollapse": "collapse"},
                        ),
                        style={"overflowX": "auto"},
                    ),
                    rx.el.div(
                        "적재된 엣지 경보가 없습니다.",
                        id="edge-alarms-empty",
                        style={"padding": "16px", "color": am.MUTED, "fontSize": "13px"},
                    ),
                ),
                style={"marginBottom": "20px"},
            ),
            id="section-edge-alarms",
        ),
        # ── Section 5: Selected Tag RAW vs COND vs FINAL Chart ──
        rx.el.div(
            am.card(
                am.section_header(
                    f"태그 시계열 비교 (RAW vs COND vs FINAL) — {EdgeMonitorState.selected_tag}",
                    subtitle="테이블에서 태그를 클릭하면 해당 태그의 원시값·전처리값·최종 확정값(BAD=NULL) 추이를 표시합니다.",
                ),
                rx.plotly(
                    data=EdgeMonitorState.tag_comparison_figure,
                    style={"width": "100%", "height": "290px"},
                ),
            ),
            id="section-vqt-chart",
        ),
    )
