"""
Communication success rate monitoring page - Light Mode Design
Shows hourly data collection statistics as a heatmap with improved UI
"""

import reflex as rx
from edgeex_app.states.communication_state import CommunicationState
from edgeex_app.components.wrapped_heatmap import wrapped_grid_heatmap
from edgeex_app.components.layout import shell


def stats_card(title: str, value: str, subtitle: str = "", color: str = "blue") -> rx.Component:
    """Improved statistics card with better spacing and Light Mode design"""

    return rx.card(
        rx.vstack(
            rx.text(title, size="2", weight="medium", color="gray"),
            rx.text(value, size="6", weight="bold", color=rx.color(color, 9)),
            rx.cond(
                subtitle != "",
                rx.text(subtitle, size="1", color="gray"),
                rx.fragment()
            ),
            spacing="1",
            align="start",
        ),
        size="2",
        variant="surface",
    )


def daily_trend_chart() -> rx.Component:
    """Daily success rate trend chart - Area chart with reference line"""

    return rx.card(
        rx.vstack(
            rx.heading("일별 성공률 트렌드", size="4"),
            rx.cond(
                CommunicationState.daily_chart_data.length() > 0,
                rx.recharts.area_chart(
                    rx.recharts.area(
                        data_key="success_rate",
                        fill=rx.color("blue", 3),
                        stroke=rx.color("blue", 7),
                        fill_opacity=0.6,
                        type_="monotone",
                    ),
                    rx.recharts.reference_line(
                        y=95,
                        stroke=rx.color("red", 7),
                        stroke_dasharray="5 5",
                        label="기준선 95%",
                    ),
                    rx.recharts.x_axis(
                        data_key="date",
                        padding={"left": 10, "right": 10},
                    ),
                    rx.recharts.y_axis(domain=[0, 100]),
                    rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                    rx.recharts.graphing_tooltip(),
                    data=CommunicationState.daily_chart_data,
                    height=CommunicationState.chart_height,
                    width="100%",
                    margin={"top": 5, "right": 5, "bottom": 0, "left": 5},
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("chart-line", size=48, color=rx.color("blue", 9)),
                        rx.text("데이터를 불러오는 중입니다", size="4", weight="bold", color=rx.color("slate", 11)),
                        rx.text("센서를 선택하고 조회 기간을 설정하세요", size="2", color=rx.color("slate", 10)),
                        spacing="3",
                        align="center",
                    ),
                    height="250px",
                    width="100%",
                    background=rx.color("gray", 2),
                    border_radius="8px",
                )
            ),
            spacing="1",
            width="100%",
        ),
        size="2",
        variant="surface",
        width="100%",
    )


@rx.page(route="/comm", on_load=CommunicationState.initialize)
def communication_page() -> rx.Component:
    """Main communication monitoring page - Light Mode"""

    return shell(
        rx.box(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.heading("통신 성공률", size="6", weight="bold"),
                    rx.badge("Real-time", variant="soft", color="green"),
                    spacing="3",
                    align="center",
                ),

                # Controls
                rx.card(
                    rx.hstack(
                        # Sensor selector
                        rx.vstack(
                            rx.text("센서 선택", size="2", weight="medium"),
                            rx.select(
                                CommunicationState.available_tags,
                                value=CommunicationState.selected_tag,
                                on_change=CommunicationState.set_selected_tag,
                                size="2",
                            ),
                            spacing="1",
                            align="start",
                        ),

                        # Period selector
                        rx.vstack(
                            rx.text("조회 기간", size="2", weight="medium"),
                            rx.segmented_control.root(
                                rx.segmented_control.item("3일", value="3"),
                                rx.segmented_control.item("7일", value="7"),
                                rx.segmented_control.item("14일", value="14"),
                                rx.segmented_control.item("30일", value="30"),
                                value=CommunicationState.selected_days_str,
                                on_change=CommunicationState.set_selected_days_str,
                                default_value="7",
                                size="2",
                            ),
                            spacing="1",
                            align="start",
                        ),

                        spacing="6",
                        align="end",
                        width="100%",
                    ),
                    size="2",
                    variant="surface",
                ),

                # Statistics cards - 4 columns
                rx.grid(
                    stats_card(
                        "평균 성공률",
                        f"{CommunicationState.overall_success_rate}%",
                        f"지난 {CommunicationState.selected_days}일",
                        rx.cond(
                            CommunicationState.overall_success_rate >= 95,
                            "green",
                            rx.cond(
                                CommunicationState.overall_success_rate >= 80,
                                "blue",
                                rx.cond(
                                    CommunicationState.overall_success_rate >= 60,
                                    "amber",
                                    "red"
                                )
                            )
                        )
                    ),
                    stats_card(
                        "전체 레코드",
                        f"{CommunicationState.total_records:,}",
                        f"예상: {CommunicationState.expected_records:,}",
                        "blue"
                    ),
                    stats_card(
                        "활성 시간",
                        CommunicationState.active_hours_str,
                        CommunicationState.total_hours_str,
                        "purple"
                    ),
                    stats_card(
                        "데이터 품질",
                        rx.cond(
                            CommunicationState.overall_success_rate >= 95,
                            "우수",
                            rx.cond(
                                CommunicationState.overall_success_rate >= 80,
                                "양호",
                                rx.cond(
                                    CommunicationState.overall_success_rate >= 60,
                                    "주의",
                                    "위험"
                                )
                            )
                        ),
                        f"{CommunicationState.selected_tag} 센서",
                        rx.cond(
                            CommunicationState.overall_success_rate >= 95,
                            "green",
                            rx.cond(
                                CommunicationState.overall_success_rate >= 80,
                                "blue",
                                rx.cond(
                                    CommunicationState.overall_success_rate >= 60,
                                    "amber",
                                    "red"
                                )
                            )
                        )
                    ),
                    columns=rx.breakpoints(initial="1", sm="2", lg="4"),
                    spacing="4",
                    width="100%",
                ),

                # Heatmap and Daily trend - responsive layout
                rx.grid(
                    # Heatmap section - FIXED: overflow handling inside card
                    rx.card(
                        rx.vstack(
                            rx.heading("시간대별 성공률 히트맵", size="4"),
                            rx.cond(
                                CommunicationState.loading,
                                rx.center(
                                    rx.vstack(
                                        rx.spinner(size="3"),
                                        rx.text("데이터 로딩 중...", size="2", color="gray"),
                                        spacing="2",
                                    ),
                                    padding="12",
                                ),
                                wrapped_grid_heatmap(CommunicationState)
                            ),
                            spacing="3",
                            width="100%",
                            overflow="hidden",  # Prevent card from expanding beyond grid
                        ),
                        size="2",
                        variant="surface",
                        width="100%",
                        min_width="0",  # Critical: Allow card to shrink below content size
                    ),
                    # Daily trend chart
                    daily_trend_chart(),
                    columns=rx.breakpoints(initial="1", lg="2"),  # 1 column on mobile, 2 on large screens
                    spacing="4",
                    width="100%",
                ),

                # Heatmap Insights and Anomalies - side by side
                rx.grid(
                    # Heatmap Pattern Insights
                    rx.card(
                        rx.vstack(
                            rx.heading("📊 히트맵 패턴 분석", size="4"),
                            rx.grid(
                                rx.vstack(
                                    rx.text("최적 시간대", size="2", color="gray"),
                                    rx.text(
                                        CommunicationState.hourly_pattern_stats['peak_hours'],
                                        size="4",
                                        weight="bold",
                                        color=rx.color("green", 9)
                                    ),
                                    rx.text("95% 이상 유지", size="1", color="gray"),
                                    spacing="1",
                                    align="start",
                                ),
                                rx.vstack(
                                    rx.text("저조 시간대", size="2", color="gray"),
                                    rx.text(
                                        CommunicationState.hourly_pattern_stats['low_hours'],
                                        size="4",
                                        weight="bold",
                                        color=rx.color("red", 9)
                                    ),
                                    rx.text("80% 미만", size="1", color="gray"),
                                    spacing="1",
                                    align="start",
                                ),
                                rx.vstack(
                                    rx.text("시간대 일관성", size="2", color="gray"),
                                    rx.text(
                                        CommunicationState.hourly_pattern_stats['consistency'],
                                        size="4",
                                        weight="bold",
                                        color=rx.color("blue", 9)
                                    ),
                                    rx.text("변동성 기준", size="1", color="gray"),
                                    spacing="1",
                                    align="start",
                                ),
                                rx.vstack(
                                    rx.text("주야 비교", size="2", color="gray"),
                                    rx.text(
                                        CommunicationState.hourly_pattern_stats['trend'],
                                        size="4",
                                        weight="bold",
                                        color=rx.color("purple", 9)
                                    ),
                                    rx.text("06-18시 vs 야간", size="1", color="gray"),
                                    spacing="1",
                                    align="start",
                                ),
                                columns=rx.breakpoints(initial="1", sm="2", md="4"),  # Responsive columns
                                spacing="4",
                                width="100%",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        size="2",
                        variant="surface",
                        width="100%",
                    ),
                    # Anomalies Detection
                    rx.cond(
                        CommunicationState.anomaly_detection.length() > 0,
                        rx.card(
                            rx.vstack(
                                rx.heading("⚠️ 이상치 탐지 (Z-score > 2)", size="4"),
                                rx.box(
                                    rx.foreach(
                                        CommunicationState.anomaly_detection,
                                        lambda item: rx.hstack(
                                            rx.text(item['timestamp'], size="2", weight="medium"),
                                            rx.text(
                                                f"{item['success_rate']}%",
                                                size="2",
                                                weight="bold",
                                                color=rx.color("red", 9)
                                            ),
                                            rx.text(
                                                f"Z: {item['z_score']}",
                                                size="1",
                                                color="gray"
                                            ),
                                            justify="between",
                                            width="100%",
                                        )
                                    ),
                                    width="100%",
                                ),
                                spacing="3",
                                width="100%",
                            ),
                            size="2",
                            variant="surface",
                        ),
                        rx.fragment()  # Empty when no anomalies
                    ),
                    columns=rx.breakpoints(initial="1", lg="2"),  # Responsive: 1 column on mobile, 2 on large screens
                    spacing="4",
                    width="100%",
                ),

                spacing="4",
                width="100%",
            ),
            padding="4",
            width="100%",
        ),
        on_mount=CommunicationState.initialize,
        active_route="/comm"
    )
