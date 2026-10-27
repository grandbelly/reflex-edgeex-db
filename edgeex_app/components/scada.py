"""Adapted from reflex-dev/templates dashboard: sidebar, navbar and card.

Upstream commit and modifications: docs/reflex_template_source.md.
"""
from collections.abc import Callable
from functools import wraps
import reflex as rx
from ..states.scada_state import ScadaState as S

NAV = [
    ("운전 개요", "layout-dashboard", "/"), ("공정 감시", "workflow", "/workflow"),
    ("트렌드", "chart-no-axes-combined", "/trend"), ("경보", "bell", "/alarms"),
    ("데이터 흐름", "network", "/edge-monitor"), ("통신 이력", "radio-tower", "/comm"),
]


def nav_item(label, icon, path, current):
    active = path == current
    return rx.link(
        rx.hstack(rx.icon(icon, size=18), rx.text(label, size="2", weight="medium"),
                  spacing="3", align="center", padding="12px 14px", border_radius="var(--radius-2)",
                  background=rx.color("teal", 3) if active else "transparent",
                  color=rx.color("teal", 11) if active else rx.color("gray", 11),
                  _hover={"background": rx.color("gray", 4)}),
        href=path, underline="none", width="100%", color="inherit",
        aria_current="page" if active else "false",
    )


def brand():
    return rx.hstack(
        rx.badge(rx.icon("activity", size=20), size="3", color_scheme="teal", padding="10px"),
        rx.vstack(rx.text("edgeEX", size="5", weight="bold"),
                  rx.text("미니 SCADA", size="1", color=rx.color("gray", 10)), spacing="0"),
        spacing="3", align="center",
    )


def sidebar(current):
    return rx.el.aside(
        rx.vstack(
            brand(), rx.separator(margin_y="12px"),
            rx.text("운전 모니터링", size="1", color=rx.color("gray", 10), margin_bottom="4px"),
            *[nav_item(*item, current) for item in NAV], rx.spacer(), rx.separator(),
            rx.hstack(rx.icon("eye", size=16), rx.text("조회 전용", size="2"), spacing="2"),
            rx.text("장치 상태와 데이터 품질을 각각 확인하세요.", size="1", color=rx.color("gray", 10)),
            padding="24px 16px", height="100%", spacing="2", align="stretch",
        ), class_name="scada-sidebar", aria_label="주 메뉴",
    )


def card(*children, **props):
    return rx.card(*children, size="3", variant="surface", class_name="scada-panel", **props)


def metric(label, value, note, icon, color="teal"):
    return card(rx.vstack(
        rx.hstack(rx.text(label, size="2", color=rx.color("gray", 11)), rx.spacer(),
                  rx.badge(rx.icon(icon, size=18), color_scheme=color, size="2"), align="center", width="100%"),
        rx.heading(value, size="8", weight="medium"),
        rx.text(note, size="1", color=rx.color("gray", 10)), align="start", spacing="3",
    ))


def quality_badge(value):
    return rx.badge(value, color_scheme=rx.match(value, ("GOOD", "teal"), ("BAD", "red"),
                                                ("UNCERTAIN", "amber"), "gray"), variant="soft")


def section_title(title, note=""):
    return rx.vstack(rx.heading(title, size="4"),
                     rx.text(note, size="2", color=rx.color("gray", 11)) if note else rx.fragment(),
                     spacing="1", align="start", margin_bottom="16px")


def scope_bar():
    def label(text, control):
        return rx.vstack(rx.text(text, size="1", weight="medium", color=rx.color("gray", 11)),
                         control, spacing="1", align="stretch")
    return card(
        rx.form(
            rx.flex(
                label("현장", rx.input(name="site", default_value=S.site_id, placeholder="현장 ID", required=True,
                                       max_length=200, width="140px", aria_label="현장 ID")),
                label("태그", rx.select(S.tags, name="tag", default_value=S.tag, placeholder="태그 선택",
                                       width="240px", aria_label="태그 선택", key=S.tag)),
                label("조회 범위", rx.select(["5", "15", "60"], name="minutes", default_value=S.minutes,
                                            width="90px", aria_label="조회 범위 (분)")),
                rx.button("적용", type="submit", variant="soft"), rx.spacer(),
                rx.button(rx.icon("refresh-cw", size=16), "지금 조회", on_click=S.refresh_now,
                          type="button", variant="outline", color_scheme="gray"),
                rx.button(rx.icon(rx.cond(S.live, "pause", "play"), size=16),
                          rx.cond(S.live, "시점 고정", "실시간 재개"), on_click=S.toggle_live,
                          type="button", variant="soft", color_scheme=rx.cond(S.live, "gray", "amber")),
                width="100%", spacing="3", align="end", wrap="wrap",
            ), on_submit=S.apply_scope, reset_on_submit=False,
        ), rx.separator(margin_y="14px"),
        rx.flex(
            rx.hstack(rx.badge(rx.cond(S.live, "5초 갱신", "시점 고정"),
                               color_scheme=rx.cond(S.live, "teal", "amber")),
                      rx.text(S.query_state, size="1"), spacing="2", align="center"),
            rx.text("현장 ", S.site_id, " · ", S.minutes, "분", size="1", color=rx.color("gray", 11)),
            rx.spacer(), rx.text("조회 기준 ", S.as_of, size="1", class_name="scada-mono", color=rx.color("gray", 10)),
            width="100%", align="center", spacing="3", wrap="wrap",
        ),
    )


def template(current: str, title: str, description: str):
    """Dashboard template wrapper shared by all six routes."""
    def decorate(content: Callable[[], rx.Component]):
        @wraps(content)
        def page():
            return rx.flex(
                sidebar(current),
                rx.box(
                    rx.box(
                        rx.flex(brand(), rx.spacer(), rx.badge("조회 전용", color_scheme="gray"),
                                padding="16px", align="center"),
                        rx.flex(*[nav_item(*item, current) for item in NAV], overflow_x="auto", padding_x="12px"),
                        display=rx.breakpoints({"0px": "block", "1024px": "none"}), border_bottom=f"1px solid {rx.color('gray', 5)}",
                    ),
                    rx.vstack(
                        rx.flex(
                            rx.vstack(rx.text("운전 모니터링 / " + title, size="1", color=rx.color("gray", 10)),
                                      rx.heading(title, size="7", weight="medium"),
                                      rx.text(description, size="2", color=rx.color("gray", 11)), spacing="2", align="start"),
                            rx.spacer(), rx.badge("검증 작업공간", color_scheme="amber", variant="outline"),
                            align="center", width="100%", wrap="wrap", spacing="3",
                        ), scope_bar(),
                        rx.cond(S.error_message != "", rx.callout(S.error_message, icon="triangle-alert", color_scheme="red", width="100%")),
                        content(),
                        rx.text("각 값의 원천 시각은 다를 수 있습니다. 조회 기준은 장치의 동시 측정 시각이 아닙니다.",
                                size="1", color=rx.color("gray", 10)),
                        rx.moment(interval=rx.cond(S.live, 5000, 0), on_change=lambda _: S.poll_tick,
                                  format="HH:mm:ss", display="none"),
                        spacing="5", align="stretch", class_name="scada-workspace",
                    ), class_name="scada-main",
                ), class_name="scada-shell", width="100%",
            )
        return page
    return decorate
