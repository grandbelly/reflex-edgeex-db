"""Stock template shell and pure presentation components for the SCADA profile."""
from collections.abc import Callable
from functools import wraps
import reflex as rx
from ..states.scada_state import ScadaState as S
from ..states.scada_display import TABLES, table_min_width

NAV = [("대시보드", "/"), ("워크플로우", "/workflow"), ("트렌드", "/trend"),
       ("경보", "/alarms"), ("통신 상태", "/comm"), ("Edge 관제", "/edge-monitor")]


def card(*children, **props):
    return rx.box(*children, class_name="scada-panel", **props)


def section_title(title, note=""):
    if isinstance(note, str):
        note = rx.text(note, class_name="note") if note else rx.fragment()
    else:
        note = rx.box(note, class_name="note")  # already text; rx.text here renders <p> inside <p>
    return rx.flex(rx.text(title, class_name="title"), rx.spacer(), note,
                   align="center", gap="12px", class_name="scada-section-head")


def pill(label, tone="neutral"):
    """Status word plus tone; tone is a State value or a literal (neutral/uncertain/bad/p1-p3)."""
    return rx.el.span(label, class_name=f"scada-pill tone-{tone}")


def quality_pill(row):
    return pill(row["quality_d"], row["tone"])


def kpi(label, value, note="", variant=""):
    return rx.box(rx.text(label, class_name="label"), rx.text(value, class_name="value"),
                  rx.text(note, class_name="note") if note else rx.fragment(),
                  class_name=f"scada-kpi {variant}")


def note(text, foot=False):
    """One factual line in place of an empty-state box."""
    return rx.box(rx.text(text), class_name="scada-note foot" if foot else "scada-note")


def facts(items):
    """Label/value rows; State already dropped unknown values."""
    return rx.box(rx.foreach(items, lambda f: rx.box(rx.text(f[0], class_name="k"),
                                                     rx.text(f[1], class_name="v"),
                                                     class_name="scada-fact")),
                  class_name="scada-detail-body")


def table(rows, name, cell=None, row_props=None):
    """Spec-driven table from scada_display.TABLES: numeric columns right-aligned,
    per-table min width so only this box scrolls."""
    spec = TABLES[name]

    def head(label, numeric):
        return rx.table.column_header_cell(label, class_name="scada-number" if numeric else "")

    def default_cell(row, key, numeric):
        if numeric:
            return rx.table.cell(row[key], class_name="scada-number")
        if key.startswith(("time", "observed", "latest")):
            return rx.table.cell(row[key], class_name="scada-time")
        return rx.table.cell(row[key])

    def body_row(row):
        cells = [(cell or {}).get(key, default_cell)(row, key, numeric) for key, _, _, numeric in spec]
        return rx.table.row(*cells, **((row_props or (lambda r: {}))(row)))

    return rx.box(rx.table.root(
        rx.table.header(rx.table.row(*[head(label, numeric) for _, label, _, numeric in spec])),
        rx.table.body(rx.foreach(rows, body_row)),
        width="100%", size="1", min_width=f"{table_min_width(name)}px"), class_name="scada-table-scroll")


def scope_bar(current):
    tag_control = (rx.select(S.tags, name="tag", default_value=S.tag, key=S.tag,
                             placeholder="태그 선택", aria_label="태그 선택", width="220px")
                   if current in {"/trend", "/edge-monitor"} else
                   rx.el.input(type="hidden", name="tag", value=S.tag))
    return rx.box(
        rx.form(rx.flex(
            rx.input(name="site", default_value=S.site_id, placeholder="현장 ID", required=True,
                     max_length=200, width="110px", aria_label="현장 ID"), tag_control,
            rx.select(["5", "15", "60"], name="minutes", default_value=S.minutes, key=S.minutes,
                      width="82px", aria_label="조회 범위 (분)"),
            rx.text("분", size="1", color="var(--muted)"),
            rx.button("적용", type="submit", size="2", variant="soft", color_scheme="gray"),
            rx.spacer(),
            rx.button(rx.icon("refresh-cw", size=14), "지금 조회", type="button",
                      on_click=S.refresh_now, size="2", variant="outline", color_scheme="gray"),
            rx.button(rx.icon(rx.cond(S.live, "pause", "play"), size=14),
                      rx.cond(S.live, "시점 고정", "실시간 재개"), type="button", on_click=S.toggle_live,
                      size="2", variant="soft", color_scheme="gray"),
            align="center", gap="10px", wrap="wrap", width="100%"),
            on_submit=S.apply_scope, reset_on_submit=False),
        rx.flex(rx.text(rx.cond(S.live, "자동 조회 · 5초", "시점 고정"), size="1"),
                rx.text(S.query_state, size="1", color="var(--muted)"), rx.spacer(),
                rx.text("조회 기준 ", S.as_of_d, " KST", size="1", class_name="scada-mono", color="var(--muted)"),
                align="center", wrap="wrap", gap="12px", margin_top="9px"),
        class_name="scada-context")


def template(current: str, title: str, description: str):
    """Stock-market top navigation, common context, menu-specific body."""
    def decorate(content: Callable[[], rx.Component]):
        @wraps(content)
        def page():
            return rx.box(
                rx.el.header(
                    rx.link(rx.hstack(rx.text("EX", weight="bold", color="var(--leaf)"),
                                      rx.text("mini SCADA", weight="bold"), spacing="2"),
                            href="/", underline="none", color="inherit", class_name="scada-brand"),
                    rx.el.nav(*[rx.link(label, href=path, underline="none", color="inherit",
                                         aria_current="page" if path == current else "false",
                                         class_name="scada-nav-link active" if path == current else "scada-nav-link")
                                for label, path in NAV], aria_label="주 메뉴", class_name="scada-navigation"),
                    rx.text("조회 전용", size="1", color="var(--muted)", class_name="scada-readonly"),
                    class_name="scada-header"),
                scope_bar(current),
                rx.el.main(
                    rx.flex(rx.box(rx.heading(title, size="6", weight="bold"),
                                   rx.text(description, size="2", color="var(--muted)", margin_top="4px")),
                            align="start", class_name="scada-page-title"),
                    rx.cond(S.error_message != "", rx.callout(S.error_message, icon="triangle-alert",
                                                               color_scheme="orange", margin_bottom="16px")),
                    content(),
                    rx.moment(interval=rx.cond(S.live, 5000, 0), on_change=lambda _: S.poll_tick,
                              format="HH:mm:ss", display="none"), class_name="scada-workspace"),
                class_name="scada-shell")
        return page
    return decorate
