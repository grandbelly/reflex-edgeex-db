"""Stock template shell and pure presentation components for the SCADA profile."""
from collections.abc import Callable
from functools import wraps
import reflex as rx
from ..states.scada_state import ScadaState as S

NAV = [("대시보드", "/"), ("워크플로우", "/workflow"), ("트렌드", "/trend"),
       ("알람", "/alarms"), ("통신 상태", "/comm"), ("Edge 관제", "/edge-monitor")]


def card(*children, **props):
    return rx.box(*children, class_name="scada-panel", **props)


def section_title(title, note=""):
    return rx.flex(rx.text(title, weight="medium"), rx.spacer(),
                   rx.text(note, size="1", color="var(--scada-muted)"),
                   align="center", gap="12px", class_name="scada-section-head")


def quality_badge(value):
    return rx.badge(rx.match(value, ("GOOD", "양호"), ("UNCERTAIN", "불확실"),
                             ("BAD", "불량"), value),
                    color_scheme=rx.match(value, ("BAD", "violet"), ("UNCERTAIN", "amber"), "gray"),
                    variant="soft", size="1")


def metric(label, value, note="", icon="", color="gray"):
    return rx.box(rx.text(label, size="1", color="var(--scada-muted)"),
                  rx.text(value, class_name="scada-stat-value"),
                  rx.text(note, size="1", color="var(--scada-muted)"), class_name="scada-stat")


def empty_state(title, detail, icon="inbox"):
    return rx.center(rx.vstack(rx.icon(icon, size=22, color="var(--scada-muted)"),
                               rx.text(title, weight="medium"),
                               rx.text(detail, size="2", color="var(--scada-muted)", text_align="center"),
                               spacing="2", align="center"), class_name="scada-empty")


def scope_bar(current):
    tag_control = (rx.select(S.tags, name="tag", default_value=S.tag, key=S.tag,
                             placeholder="태그 선택", aria_label="태그 선택", width="220px")
                   if current in {"/trend", "/edge-monitor"} else
                   rx.el.input(type="hidden", name="tag", value=S.tag))
    return rx.box(
        rx.form(rx.flex(
            rx.input(name="site", default_value=S.site_id, placeholder="현장 ID", required=True,
                     max_length=200, width="110px", aria_label="현장 ID"), tag_control,
            rx.select(["5", "15", "60"], name="minutes", default_value=S.minutes,
                      width="82px", aria_label="조회 범위 (분)"),
            rx.text("분", size="1", color="var(--scada-muted)"),
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
                rx.text(S.query_state, size="1", color="var(--scada-muted)"), rx.spacer(),
                rx.text("조회 기준 ", S.as_of, size="1", class_name="scada-mono", color="var(--scada-muted)"),
                align="center", wrap="wrap", gap="12px", margin_top="9px"),
        class_name="scada-context")


def template(current: str, title: str, description: str):
    """Stock-market top navigation, common context, menu-specific body."""
    def decorate(content: Callable[[], rx.Component]):
        @wraps(content)
        def page():
            return rx.box(
                rx.el.header(
                    rx.link(rx.hstack(rx.text("EX", weight="bold", color="var(--scada-accent)"),
                                      rx.text("mini SCADA", weight="bold"), spacing="2"),
                            href="/", underline="none", color="inherit", class_name="scada-brand"),
                    rx.el.nav(*[rx.link(label, href=path, underline="none", color="inherit",
                                         aria_current="page" if path == current else "false",
                                         class_name="scada-nav-link active" if path == current else "scada-nav-link")
                                for label, path in NAV], aria_label="주 메뉴", class_name="scada-navigation"),
                    rx.text("조회 전용", size="1", color="var(--scada-muted)", class_name="scada-readonly"),
                    class_name="scada-header"),
                scope_bar(current),
                rx.el.main(
                    rx.flex(rx.box(rx.heading(title, size="5", weight="medium"),
                                   rx.text(description, size="2", color="var(--scada-muted)", margin_top="4px")),
                            align="start", class_name="scada-page-title"),
                    rx.cond(S.error_message != "", rx.callout(S.error_message, icon="triangle-alert",
                                                               color_scheme="orange", margin_bottom="16px")),
                    content(),
                    rx.el.footer("원천 시각과 적재 시각을 구분합니다. 조회 기준은 장치의 동시 측정을 뜻하지 않습니다.",
                                 class_name="scada-footer"),
                    rx.moment(interval=rx.cond(S.live, 5000, 0), on_change=lambda _: S.poll_tick,
                              format="HH:mm:ss", display="none"), class_name="scada-workspace"),
                class_name="scada-shell")
        return page
    return decorate
