"""
실시간 알람 페이지 - Light Mode 개선 버전
작성일: 2025-09-26
수정일: 2025-10-02 (Light Mode 디자인 개선)
"""

import reflex as rx
from ..states.alarm_rt_state import AlarmRTState as A
from ..components.layout import shell
from ..components.page_header import page_header
from ..components.alarms import (
    stat_card,
    filter_bar,
    live_indicator,
    action_bar,
)


@rx.page(
    route="/alarms_rt",
    title="실시간 알람 상태",
    on_load=[A.load_all_data]
)
def alarms_rt_page() -> rx.Component:
    """실시간 알람 대시보드 - Light Mode"""
    return shell(
        rx.vstack(
            # Header - 통일된 디자인
            page_header(
                title="알람 대시보드",
                icon="bell",
                actions=rx.hstack(
                    live_indicator(
                        is_live=True,
                        last_update=A.last_update,
                    ),
                    rx.button(
                        rx.icon("refresh-cw", size=16),
                        " 새로고침",
                        size="2",
                        variant="soft",
                        color_scheme="blue",
                        on_click=A.load_all_data,
                    ),
                    spacing="3",
                    align="center"
                )
            ),

            # Sensor Status Cards (Total, Normal, Warning, Critical)
            rx.grid(
                stat_card(
                    title="Total Sensors",
                    value=A.total_sensors_count,
                    icon="cpu",
                    color="gray",
                ),
                stat_card(
                    title="Normal",
                    value=A.normal_sensors_count,
                    icon="circle-check",
                    color="green",
                ),
                stat_card(
                    title="주의 알람",
                    value=A.warning_sensors_count,
                    icon="triangle-alert",
                    color="orange",
                ),
                stat_card(
                    title="위험 알람",
                    value=A.critical_sensors_count,
                    icon="circle-alert",
                    color="red",
                ),
                columns=rx.breakpoints(
                    initial="2",
                    xs="2",
                    sm="4",
                    md="4",
                    lg="4",
                ),
                gap="4",
                width="100%",
            ),

            # All Sensor Status Cards (detailed view)
            rx.vstack(
                rx.heading("🔍 All Sensor Status", size="3", color="#E8F0FA"),
                rx.grid(
                    rx.foreach(
                        A.all_sensors,
                        lambda sensor: rx.box(
                            rx.vstack(
                                # Header
                                rx.flex(
                                    rx.text(
                                        sensor["tag_name"],
                                        size="2",
                                        weight="bold",
                                        color="#E8F0FA",
                                    ),
                                    rx.badge(
                                        sensor["status"],
                                        size="1",
                                        variant="solid",
                                        color_scheme=rx.cond(
                                            sensor["status"] == "CRITICAL",
                                            "red",
                                            rx.cond(
                                                sensor["status"] == "WARNING",
                                                "orange",
                                                "green"
                                            )
                                        ),
                                    ),
                                    justify="between",
                                    width="100%",
                                ),
                                # Description
                                rx.text(
                                    sensor["description"],
                                    size="1",
                                    color="#8DA2C0",
                                ),
                                # Value
                                rx.flex(
                                    rx.text(
                                        f"{sensor['value']:.2f}",
                                        size="3",
                                        weight="bold",
                                        color="#E8F0FA",
                                    ),
                                    rx.text(
                                        sensor["unit"],
                                        size="1",
                                        color="#6E8093",
                                    ),
                                    gap="1",
                                    align="baseline",
                                ),
                                # Range
                                rx.text(
                                    f"Range: {sensor['min_val']:.2f} ~ {sensor['max_val']:.2f}",
                                    size="1",
                                    color="#6E8093",
                                ),
                                # Timestamp
                                rx.text(
                                    sensor["timestamp"],
                                    size="1",
                                    color="#6E8093",
                                ),
                                spacing="2",
                                align="start",
                            ),
                            padding="3",
                            bg="var(--ks-panel)",
                            border="1px solid #22384E",
                            border_radius="md",
                            _hover={"border_color": "#3b82f6"},
                        )
                    ),
                    columns=rx.breakpoints(
                        initial="2",
                        xs="2",
                        sm="3",
                        md="4",
                        lg="6",
                    ),
                    gap="3",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),

            # Alarm Statistics Cards (6 cards in grid)
            rx.grid(
                stat_card(
                    title="전체 알람",
                    value=A.total_alarm_count,
                    icon="database",
                    color="gray",
                ),
                stat_card(
                    title="위험 알람",
                    value=A.critical_count,
                    icon="circle-alert",
                    color="red",
                ),
                stat_card(
                    title="주의 알람",
                    value=A.warning_count,
                    icon="triangle-alert",
                    color="orange",
                ),
                stat_card(
                    title="정보 알람",
                    value=A.normal_count,
                    icon="info",
                    color="blue",
                ),
                stat_card(
                    title="미확인 알람",
                    value=A.unacknowledged_count,
                    icon="bell",
                    color="orange",
                ),
                stat_card(
                    title="확인완료",
                    value=A.acknowledged_count,
                    icon="circle-check",
                    color="green",
                ),
                columns=rx.breakpoints(
                    initial="2",
                    xs="2",
                    sm="3",
                    md="6",
                    lg="6",
                ),
                gap="4",
                width="100%",
            ),

            # Filter Bar
            filter_bar(
                search_value="",
                severity_filter="all",
                status_filter="all",
            ),

            # Action Bar
            action_bar(
                shown_count=A.total_alarm_count,
                selected_count=0,
            ),

            # Alarm List
            rx.vstack(
                rx.cond(
                    A.realtime_alarms,
                    rx.vstack(
                        rx.foreach(
                            A.realtime_alarms,
                            lambda alarm: rx.box(
                                rx.vstack(
                                    # Header row
                                    rx.flex(
                                        rx.flex(
                                            rx.badge(
                                                alarm["status"],
                                                size="2",
                                                variant="solid",
                                                color_scheme=rx.cond(
                                                    alarm["status"] == "CRITICAL",
                                                    "red",
                                                    rx.cond(
                                                        alarm["status"] == "WARNING",
                                                        "orange",
                                                        "blue"
                                                    )
                                                ),
                                            ),
                                            rx.text(
                                                alarm["tag_name"],
                                                size="2",
                                                weight="bold",
                                                color="#E8F0FA",
                                            ),
                                            gap="2",
                                            align="center",
                                        ),
                                        rx.spacer(),
                                        rx.flex(
                                            rx.text(
                                                alarm["last_alarm_time"],
                                                size="2",
                                                color="#8DA2C0",
                                            ),
                                            rx.button(
                                                "Acknowledge",
                                                size="2",
                                                variant="soft",
                                                color_scheme="blue",
                                                on_click=lambda: A.acknowledge_alarm(alarm["tag_name"]),
                                            ),
                                            gap="2",
                                            align="center",
                                        ),
                                        justify="between",
                                        align="center",
                                        width="100%",
                                    ),

                                    # Details row
                                    rx.flex(
                                        rx.vstack(
                                            rx.text("현재값", size="1", color="#6E8093"),
                                            rx.text(
                                                f"{alarm['current_value']:.2f}",
                                                size="2",
                                                weight="bold",
                                                color="#E8F0FA",
                                            ),
                                            spacing="1",
                                            align="start",
                                        ),
                                        rx.vstack(
                                            rx.text("임계값", size="1", color="#6E8093"),
                                            rx.text(
                                                f"{alarm['threshold_low']:.2f} ~ {alarm['threshold_high']:.2f}",
                                                size="2",
                                                color="#E8F0FA",
                                            ),
                                            spacing="1",
                                            align="start",
                                        ),
                                        rx.vstack(
                                            rx.text("시나리오", size="1", color="#6E8093"),
                                            rx.badge(
                                                alarm["scenario"],
                                                size="2",
                                                variant="soft",
                                                color_scheme=rx.cond(
                                                    alarm["scenario"] == "AI_BASE",
                                                    "purple",
                                                    "blue"
                                                ),
                                            ),
                                            spacing="1",
                                            align="start",
                                        ),
                                        gap="6",
                                        width="100%",
                                    ),

                                    spacing="3",
                                ),
                                padding="4",
                                bg="var(--ks-panel)",
                                border="1px solid #22384E",
                                border_radius="lg",
                                _hover={"border_color": "#3b82f6"},
                            )
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    # No data state
                    rx.center(
                        rx.vstack(
                            rx.icon("inbox", size=48, color="#6E8093"),
                            rx.text(
                                "알람이 없습니다",
                                size="4",
                                weight="bold",
                                color="#8DA2C0",
                            ),
                            rx.text(
                                "필터를 조정하거나 새로고침하세요",
                                size="2",
                                color="#6E8093",
                            ),
                            spacing="3",
                        ),
                        padding="12",
                    ),
                ),
                width="100%",
            ),

            # Pagination
            rx.flex(
                rx.text(
                    f"Showing {A.total_alarm_count} alarms",
                    size="2",
                    color="#8DA2C0",
                ),
                rx.button(
                    "Load More",
                    size="2",
                    variant="soft",
                    color_scheme="gray",
                ),
                justify="between",
                align="center",
                padding="3",
                bg="#192D40",
                border_radius="md",
                width="100%",
            ),

            spacing="4",
            padding="4",
            width="100%",
            class_name="min-h-screen",
        ),
        active_route="/alarms_rt",
    )