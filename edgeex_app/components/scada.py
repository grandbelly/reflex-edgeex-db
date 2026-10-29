"""designs/design_guide.md shell and presentation components for the SCADA profile.
Colours come only from `--am-*` tokens in assets/scada.css; components never name a colour."""
from collections.abc import Callable
from functools import wraps
import reflex as rx
from ..states.scada_state import ScadaState as S
from ..states.scada_display import TABLES, table_min_width

NAV = [("대시보드", "/"), ("워크플로우", "/workflow"), ("트렌드", "/trend"),
       ("경보", "/alarms"), ("통신 상태", "/comm"), ("Edge 관제", "/edge-monitor")]


def card(*children, raised=False, **props):
    return rx.box(*children, class_name="scada-panel raised" if raised else "scada-panel", **props)


def section_title(title, note="", right=None):
    """Card title (h3) with its one-line note underneath; `right` holds a pill or count."""
    if isinstance(note, str):
        note = rx.el.p(note, class_name="note") if note else rx.fragment()
    else:
        note = rx.box(note, class_name="note")  # already text; a <p> here renders <p> inside <p>
    return rx.box(rx.box(rx.el.h3(title, class_name="title"), note, min_width="0"),
                  right if right is not None else rx.fragment(), class_name="scada-section-head")


def pill(label, tone="neutral"):
    """Status word plus tone; tone is a State value or a literal (good/uncertain/bad/info/neutral)."""
    return rx.el.span(label, class_name=f"scada-pill tone-{tone}")


def quality_pill(row):
    return pill(row["quality_d"], row["tone"])


def kpi(label, value, desc="", variant="", icon=None, unit=None):
    """KPI tile §7.1: mono label + icon, 34 px value, foot description."""
    return rx.box(
        rx.box(rx.box(rx.el.span(label, class_name="label"),
                      rx.icon(icon, size=16, class_name="icon") if icon else rx.fragment(),
                      class_name="meta"),
               rx.box(rx.el.span(value, class_name="value"),
                      rx.el.span(unit, class_name="desc") if unit else rx.fragment(),
                      display="flex", align_items="baseline", gap="4px")),
        rx.el.span(desc, class_name="desc") if desc else rx.fragment(),
        class_name=f"scada-kpi {variant}")


def note(text, foot=False):
    """One factual line in place of an empty-state box."""
    return rx.box(rx.text(text), class_name="scada-note foot" if foot else "scada-note")


def facts(items):
    """Label/value rows; State already dropped unknown values."""
    return rx.box(rx.foreach(items, lambda f: rx.box(rx.el.span(f[0], class_name="k"),
                                                     rx.el.span(f[1], class_name="v"),
                                                     class_name="scada-fact")),
                  class_name="scada-detail-body")


def button(*children, kind="secondary", **props):
    return rx.el.button(*children, type=props.pop("type", "button"), class_name=f"scada-btn {kind}", **props)


def icon_button(icon, label, flat=False, **props):
    return rx.el.button(rx.icon(icon, size=14), type="button", aria_label=label, title=label,
                        class_name="scada-icon-btn flat" if flat else "scada-icon-btn", **props)


def segment(options, current, on_pick):
    """Pill segment §7.3: `options` are (value, label); `on_pick(value)` returns the event."""
    return rx.box(*[rx.el.button(label, type="button", on_click=on_pick(value),
                                 class_name=rx.cond(current == value, "on", ""))
                    for value, label in options], class_name="scada-segment")


def select(name, options, value, label):
    """Native select §7.2 with the chevron overlay; `options` is a list or a list Var."""
    items = (rx.foreach(options, lambda o: rx.el.option(o, value=o)) if isinstance(options, rx.Var)
             else [rx.el.option(text, value=v) for v, text in options])
    return rx.box(rx.el.select(items, name=name, default_value=value, key=value, aria_label=label,
                               class_name="scada-select"),
                  rx.icon("chevron-down", size=14, class_name="chev"), class_name="scada-select-wrap")


def search(value, on_change, placeholder):
    return rx.box(rx.icon("search", size=16, class_name="icon"),
                  rx.debounce_input(rx.el.input(value=value, on_change=on_change, placeholder=placeholder,
                                                aria_label=placeholder, type="search"), debounce_timeout=300),
                  class_name="scada-search")


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


def theme_toggle():
    """§0: every token flips with the <html> class; dark shows the sun, light the moon."""
    return rx.el.button(rx.color_mode_cond(light=rx.icon("moon", size=16), dark=rx.icon("sun", size=16)),
                        type="button", on_click=rx.toggle_color_mode, aria_label="밝기 전환",
                        title="밝기 전환", class_name="scada-icon-btn")


def header(title):
    return rx.el.header(
        rx.box(rx.link(rx.box(rx.icon("activity", size=20), class_name="scada-logo"),
                       rx.box(rx.el.div("mini SCADA", class_name="name"),
                              rx.el.div("edgeEX · 조회 전용", class_name="sub")),
                       href="/", underline="none", class_name="scada-brand"),
               rx.el.nav(rx.el.span("현장 ", S.site_id), rx.el.span("/"), rx.el.span(title, class_name="here"),
                         aria_label="현재 위치", class_name="scada-crumbs"),
               display="flex", align_items="center", gap="24px", min_width="0"),
        rx.box(pill(S.query_state, rx.cond(S.query_state.contains("실패"), "bad", "info")),
               rx.el.button(rx.icon("refresh-cw", size=12), rx.cond(S.live, "실시간", "시점 고정"),
                            type="button", on_click=S.toggle_live, aria_pressed=S.live,
                            class_name=rx.cond(S.live, "scada-btn small live", "scada-btn small paused")),
               theme_toggle(), class_name="scada-header-actions"),
        class_name="scada-header")


def scope_bar(current):
    """Variables row: scope inputs submit together; counts and time stay read-only."""
    tag_control = (rx.box(rx.el.span("태그", class_name="scada-var-label"),
                          select("tag", S.tags, S.tag, "태그 선택"), class_name="scada-var")
                   if current in {"/trend", "/edge-monitor"} else
                   rx.el.input(type="hidden", name="tag", value=S.tag))
    return rx.form(rx.box(
        rx.box(rx.el.span("현장", class_name="scada-var-label"),
               rx.el.input(name="site", default_value=S.site_id, placeholder="현장 ID", required=True,
                           max_length=200, aria_label="현장 ID", class_name="scada-input", size=10),
               class_name="scada-var"),
        tag_control,
        rx.box(rx.el.span("범위", class_name="scada-var-label"),
               select("minutes", [("5", "최근 5분"), ("15", "최근 15분"), ("60", "최근 60분")], S.minutes,
                      "조회 범위"), class_name="scada-var"),
        button("적용", type="submit", kind="secondary small"),
        rx.el.span(class_name="divider"),
        rx.el.span(rx.cond(S.live, "자동 조회 · 5초", "시점 고정"), class_name="scada-var-label"),
        rx.el.span("조회 기준 ", S.as_of_d, " KST", class_name="asof"),
        class_name="scada-vars"), on_submit=S.apply_scope, reset_on_submit=False)


def subnav(current):
    return rx.box(
        rx.el.nav(*[rx.link(label, href=path, underline="none",
                            aria_current="page" if path == current else "false",
                            class_name="scada-tab active" if path == current else "scada-tab")
                    for label, path in NAV], aria_label="주 메뉴", class_name="scada-tabs"),
        button(rx.icon("refresh-cw", size=14), "지금 조회", kind="primary", on_click=S.refresh_now),
        class_name="scada-subnav")


def template(current: str, title: str, description: str):
    """metrics-dashboard shell: header h-14, variables row, sub-nav tabs, p-6 body."""
    def decorate(content: Callable[[], rx.Component]):
        @wraps(content)
        def page():
            return rx.box(
                header(title), scope_bar(current), subnav(current),
                rx.el.main(
                    rx.box(rx.el.h1(title), rx.el.p(description), class_name="scada-page-title"),
                    rx.cond(S.error_message != "",
                            rx.box(rx.icon("shield-alert", size=18), rx.text(S.error_message),
                                   class_name="scada-banner", role="alert")),
                    content(),
                    rx.moment(interval=rx.cond(S.live, 5000, 0), on_change=lambda _: S.poll_tick,
                              format="HH:mm:ss", display="none"), class_name="scada-workspace"),
                class_name="scada-shell")
        return page
    return decorate
