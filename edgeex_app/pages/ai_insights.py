"""AI Insights page for sensor data analysis and decision support."""

import reflex as rx
from edgeex_app.components.layout import shell
from edgeex_app.states.ai_state import AIState
from edgeex_app.components.ai_visualizations import (
    sensor_status_heatmap, 
    sensor_comparison_bar, 
    qc_violations_chart,
    data_count_pie_chart,
    sensor_trend_chart
)


def chat_interface() -> rx.Component:
    """Main chat interface component."""
    return rx.el.div(
        rx.cond(
            AIState.messages,
            # 메시지가 있을 때 - 채팅 모드
            rx.auto_scroll(
                rx.foreach(
                    AIState.messages,
                    lambda m, i: message_bubble(
                        m["text"],
                        m["is_ai"],
                        i == AIState.messages.length() - 1,
                        m.get("visualization_data"),
                    ),
                ),
                class_name="flex flex-col gap-4 pb-24 pt-6 px-4 flex-1",
            ),
            # 메시지가 없을 때 - 웰컴 화면
            welcome_cards(),
        ),
        # 동적 입력창 위치
        rx.cond(
            AIState.messages,
            # 메시지가 있을 때 - 하단 고정
            input_area_bottom(),
            # 메시지가 없을 때 - 중앙 위치 (웰컴 카드 하단)
            input_area_center(),
        ),
        class_name="h-full flex flex-col bg-gray-50 w-full relative",
    )


def sensor_status_card(sensor) -> rx.Component:
    """Individual sensor status card component."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(sensor['sensor'], class_name="font-medium text-sm"),
            rx.el.div(f"{sensor['value']}", class_name="text-lg font-bold"),
            rx.el.div(
                rx.cond(
                    sensor['status'] == "normal",
                    "✅ 정상",
                    rx.cond(
                        sensor['status'] == "warning",
                        "⚠️ 주의",
                        "🚨 위험"
                    )
                ),
                class_name="text-xs"
            )
        ),
        class_name=rx.cond(
            sensor['status'] == "normal",
            "bg-green-50 border border-green-200 rounded-lg p-3 text-center",
            rx.cond(
                sensor['status'] == "warning",
                "bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-center",
                "bg-red-50 border border-red-200 rounded-lg p-3 text-center"
            )
        )
    )



def violation_item(violation) -> rx.Component:
    """Individual violation item component."""
    return rx.el.div(
        f"🚨 {violation['sensor']}: {violation['value']} (임계값: {violation['max_val']})",
        class_name="text-red-600 text-sm mb-1 p-2 bg-red-50 rounded"
    )


def correlation_heatmap_component() -> rx.Component:
    """상관관계 히트맵 컴포넌트"""
    return rx.el.div(
        rx.el.h4("🔗 센서 상관관계 분석", class_name="text-sm font-medium text-gray-700 mb-3"),
        
        # 상관관계 매트릭스 표시
        rx.cond(
            AIState.get_correlation_sensors,
            rx.el.div(
                rx.el.p("📊 분석된 센서", class_name="text-xs text-gray-600 mb-2"),
                rx.el.div(
                    rx.foreach(
                        AIState.get_correlation_sensors,
                        lambda sensor: rx.el.span(
                            sensor,
                            class_name="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded mr-2 mb-1"
                        )
                    ),
                    class_name="mb-2"
                ),
                # 상관계수 매트릭스 텍스트 표시
                rx.cond(
                    AIState.get_correlation_matrix_rows,
                    rx.el.div(
                        rx.el.p("📈 상관계수 매트릭스", class_name="text-xs text-gray-600 mb-1"),
                        rx.el.div(
                            rx.foreach(
                                AIState.get_correlation_matrix_rows,
                                lambda row: rx.el.div(
                                    row,
                                    class_name="text-xs font-mono bg-gray-100 p-1 rounded mb-1"
                                )
                            ),
                            class_name="space-y-1"
                        ),
                        class_name="mb-3"
                    )
                )
            )
        ),
        
        # 인사이트 요약
        rx.el.div(
            rx.cond(
                AIState.get_correlation_summary,
                # 실제 분석 결과가 있을 때
                rx.el.div(
                    rx.foreach(
                        AIState.get_correlation_summary,
                        lambda insight: rx.el.div(
                            f"• {insight}",
                            class_name="text-xs text-gray-700 mb-1"
                        )
                    ),
                    class_name="space-y-1"
                ),
                # 분석 결과가 없을 때 기본 메시지
                rx.el.div(
                    "📊 상관관계 분석이 완료되었습니다.",
                    class_name="text-xs text-gray-700 mb-1"
                )
            ),
            class_name="bg-blue-50 p-3 rounded"
        ),
        class_name="mt-4 p-3 bg-gray-50 rounded-lg"
    )


def predictions_component() -> rx.Component:
    """예측 분석 컴포넌트"""
    return rx.el.div(
        rx.el.h4("🔮 센서 값 예측 분석", class_name="text-sm font-medium text-gray-700 mb-3"),
        rx.cond(
            AIState.get_predictions_data,
            # 실제 예측 데이터가 있을 때
            rx.foreach(
                AIState.get_predictions_data,
                lambda pred: prediction_chart_item(pred)
            ),
            # 예측 데이터가 없을 때 기본 차트
            rx.el.div(
                rx.el.p("🔮 XGBoost 및 RandomForest 모델을 사용한 예측 분석이 진행되었습니다.", 
                       class_name="text-xs text-gray-700 mb-2"),
                rx.el.div(
                    "더 많은 데이터가 수집되면 더 정확한 예측 차트가 표시됩니다.",
                    class_name="text-xs text-gray-600"
                ),
                class_name="bg-purple-50 p-3 rounded"
            )
        ),
        class_name="mt-4 p-3 bg-gray-50 rounded-lg"
    )


def prediction_chart_item(pred) -> rx.Component:
    """Individual prediction chart item."""
    return rx.el.div(
        rx.el.h5(
            f"📈 {pred['sensor']} 예측",
            class_name="text-xs font-medium text-blue-700 mb-2"
        ),
        rx.recharts.line_chart(
            rx.recharts.line(
                data_key="predicted",
                stroke="#8884d8",
                stroke_width=2,
                name="예측값"
            ),
            rx.recharts.x_axis(data_key="time"),
            rx.recharts.y_axis(),
            rx.recharts.tooltip(),
            rx.recharts.legend(),
            data=pred["data"],
            width="100%",
            height=200
        ),
        class_name="bg-purple-50 p-3 rounded mb-3"
    )


def anomalies_component() -> rx.Component:
    """이상치 탐지 결과 컴포넌트"""
    return rx.el.div(
        rx.el.h4("🚨 이상치 탐지 결과", class_name="text-sm font-medium text-gray-700 mb-3"),
        rx.foreach(
            AIState.get_anomalies_data,
            lambda anomaly: anomaly_item(anomaly)
        ),
        class_name="mt-4 p-3 bg-gray-50 rounded-lg"
    )


def anomaly_item(anomaly) -> rx.Component:
    """Individual anomaly item."""
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                "🔴",
                class_name="mr-2"
            ),
            rx.el.span(
                f"{anomaly['sensor']}: {anomaly['value']}",
                class_name="font-medium text-sm"
            ),
            class_name="flex items-center"
        ),
        rx.el.div(
            f"이상도: {anomaly.get('anomaly_score', 0):.2f}",
            class_name="text-xs text-gray-500 ml-6"
        ),
        class_name="p-2 bg-red-50 border-l-4 border-red-400 mb-2"
    )


def comprehensive_component() -> rx.Component:
    """종합 분석 요약 컴포넌트"""
    return rx.el.div(
        rx.el.h4("📊 종합 분석 요약", class_name="text-sm font-medium text-gray-700 mb-3"),
        rx.el.div(
            # 분석 메타데이터 표시
            rx.cond(
                AIState.get_analysis_metadata,
                rx.el.div(
                    rx.el.div(
                        rx.el.span("분석 완료", class_name="font-medium text-xs text-green-600"),
                    ),
                    class_name="mb-3"
                )
            ),
            # 인사이트 목록
            rx.foreach(
                AIState.get_analysis_insights,
                lambda insight: rx.el.div(
                    f"💡 {insight}",
                    class_name="text-xs text-gray-700 mb-1 p-2 bg-blue-50 rounded"
                )
            ),
            class_name="space-y-2"
        ),
        class_name="mt-4 p-3 bg-gray-50 rounded-lg"
    )


def render_visualizations(viz_data, is_ai) -> rx.Component:
    """Render AI visualization components based on viz_data."""
    return rx.el.div(
        # 1. 센서 상태 - AI 응답이 있을 때 항상 표시
        rx.cond(
            is_ai,
            rx.el.div(
                rx.el.h4("📊 센서 현재 상태", class_name="text-sm font-medium text-gray-700 mb-3"),
                rx.el.div(
                    rx.cond(
                        AIState.get_parsed_sensor_data,
                        # 센서 데이터가 있을 때
                        rx.foreach(
                            AIState.get_parsed_sensor_data,
                            sensor_status_card
                        ),
                        # 센서 데이터가 없을 때 로딩 표시
                        rx.el.div(
                            rx.icon("loader-circle", class_name="animate-spin"),
                            "데이터 로딩 중...",
                            class_name="flex items-center gap-2 text-gray-500 text-sm"
                        )
                    ),
                    class_name="grid grid-cols-3 gap-3"
                ),
                class_name="mt-4 p-3 bg-gray-50 rounded-lg"
            )
        ),
        # 2. 추가 시각화는 데이터가 있을 때만 표시
        rx.cond(
            is_ai & AIState.has_visualization_data,
            rx.el.div(
            # 2. 판다스 상관관계 히트맵
            rx.cond(
                AIState.has_correlation_heatmap,
                correlation_heatmap_component()
                ),
                # 3. 판다스 예측 분석 차트
                rx.cond(
                    AIState.has_predictions,
                    predictions_component()
                ),
                # 4. 판다스 이상치 탐지 결과
                rx.cond(
                    AIState.has_anomalies,
                    anomalies_component()
                ),
                # 5. 판다스 종합 분석 요약
                rx.cond(
                    AIState.has_comprehensive,
                    comprehensive_component()
                ),
                # 3. 센서 값 비교 - 막대차트 유지
                rx.cond(
                    AIState.get_comparison_data,
                    rx.el.div(
                        rx.el.h4("📈 센서 값 비교", class_name="text-sm font-medium text-gray-700 mb-2"),
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="value",
                                fill="#3b82f6"
                            ),
                            rx.recharts.x_axis(data_key="sensor"),
                            rx.recharts.y_axis(),
                            rx.recharts.tooltip(),
                            data=AIState.get_comparison_data,
                            width="100%",
                            height=250
                        ),
                        class_name="mt-4 p-3 bg-gray-50 rounded-lg"
                    )
                ),
                # 4. 트렌드 차트 - 라인 차트
                rx.cond(
                    AIState.get_trend_data,
                    rx.el.div(
                        rx.el.h4("📉 센서 트렌드", class_name="text-sm font-medium text-gray-700 mb-2"),
                        rx.recharts.line_chart(
                            rx.recharts.line(
                                data_key="value",
                                stroke="#8884d8",
                                stroke_width=2
                            ),
                            rx.recharts.x_axis(data_key="time"),
                            rx.recharts.y_axis(),
                            rx.recharts.tooltip(),
                            data=AIState.get_trend_data,
                            width="100%",
                            height=250
                        ),
                        class_name="mt-4 p-3 bg-gray-50 rounded-lg"
                    )
                ),
                # 5. QC 위반 현황
                rx.cond(
                    AIState.get_violations_data,
                    rx.el.div(
                        rx.el.h4("⚠️ QC 위반 센서", class_name="text-sm font-medium text-gray-700 mb-2"),
                        rx.foreach(
                            AIState.get_violations_data,
                            violation_item
                        ),
                        class_name="mt-4 p-3 bg-gray-50 rounded-lg"
                    )
                ),
                class_name="space-y-4"
            )
        )
    )


def message_bubble(text: str, is_ai: bool, is_last: bool, viz_data: dict = None) -> rx.Component:
    """Individual message bubble component."""
    return rx.el.div(
        rx.el.div(
            rx.cond(
                is_ai,
                rx.el.div(
                    rx.icon("bot", size=20),
                    class_name="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center flex-shrink-0",
                ),
                rx.el.div(
                    rx.icon("user", size=20),
                    class_name="w-8 h-8 bg-gray-500 text-white rounded-full flex items-center justify-center flex-shrink-0",
                ),
            ),
            rx.el.div(
                rx.el.div(
                    text,
                    class_name="whitespace-pre-wrap"  # 줄바꿈과 공백 보존
                ),
                # AI 응답에 시각화 데이터가 있으면 표시
                render_visualizations(viz_data, is_ai),
                class_name=rx.cond(
                    is_ai,
                    "bg-white border border-gray-200 rounded-lg p-3 max-w-5xl",
                    "bg-blue-500 text-white rounded-lg p-3 max-w-3xl",
                ),
            ),
            class_name=rx.cond(
                is_ai,
                "flex gap-3 items-start",
                "flex gap-3 items-start flex-row-reverse ml-12",
            ),
        ),
        rx.cond(
            AIState.typing & is_ai & is_last,
            rx.el.div(
                rx.icon("loader-circle", class_name="animate-spin"),
                "분석 중...",
                class_name="flex items-center gap-2 text-gray-500 text-sm ml-11 mt-2",
            ),
        ),
        class_name="w-full",
    )


def input_area_bottom() -> rx.Component:
    """Chat input area component - bottom fixed position for chat mode."""
    return rx.el.div(
        rx.el.div(
            rx.el.form(
                rx.el.textarea(
                    name="message",
                    placeholder="센서 데이터에 대해 질문해보세요 (예: D101 센서 현재 상태는?)",
                    enter_key_submit=True,
                    class_name="bg-transparent resize-none outline-none text-base py-4 px-5 min-h-14 text-black max-h-32 peer !overflow-y-auto",
                    auto_height=True,
                    required=True,
                ),
                rx.box(
                    rx.el.button(
                        rx.icon("square-pen", size=16),
                        title="새 대화",
                        class_name="rounded-full bg-white text-gray-500 p-2 shadow-sm size-9 inline-flex items-center justify-center hover:bg-gray-100 border transition-colors",
                        type="button",
                        on_click=AIState.clear_messages,
                    ),
                    rx.el.button(
                        rx.cond(
                            AIState.typing,
                            rx.icon("loader-circle", class_name="animate-spin"),
                            rx.icon("arrow-up"),
                        ),
                        class_name="self-end rounded-full bg-blue-500 text-white p-2 disabled:opacity-50 shadow-sm size-9 inline-flex items-center justify-center hover:bg-blue-600 transition-colors",
                        disabled=AIState.typing,
                    ),
                    class_name="flex flex-row mb-2 peer-placeholder-shown:[&>*:last-child]:opacity-50 peer-placeholder-shown:[&>*:last-child]:pointer-events-none w-full justify-between",
                ),
                reset_on_submit=True,
                on_submit=AIState.send_message,
                class_name="flex flex-col gap-2",
            ),
            class_name="rounded-2xl bg-white w-full border border-gray-200 px-4 py-2 shadow-lg mx-auto z-10 focus-within:ring-blue-100 focus-within:ring-2 focus-within:border-blue-300 transition-all",
        ),
        class_name="px-6 absolute bottom-6 left-0 right-0 max-w-6xl mx-auto",
    )


def input_area_center() -> rx.Component:
    """Chat input area component - center position for welcome screen."""
    return rx.el.div(
        rx.el.div(
            rx.el.form(
                rx.el.textarea(
                    name="message",
                    placeholder="센서 데이터에 대해 질문해보세요 (예: D101 센서 현재 상태는?)",
                    enter_key_submit=True,
                    class_name="bg-transparent resize-none outline-none text-base py-4 px-5 min-h-14 text-black max-h-32 peer !overflow-y-auto",
                    auto_height=True,
                    required=True,
                ),
                rx.box(
                    rx.el.button(
                        rx.cond(
                            AIState.typing,
                            rx.icon("loader-circle", class_name="animate-spin"),
                            rx.icon("arrow-up"),
                        ),
                        class_name="self-end rounded-full bg-blue-500 text-white p-2 disabled:opacity-50 shadow-sm size-9 inline-flex items-center justify-center hover:bg-blue-600 transition-colors",
                        disabled=AIState.typing,
                    ),
                    class_name="flex flex-row mb-2 peer-placeholder-shown:[&>*:last-child]:opacity-50 peer-placeholder-shown:[&>*:last-child]:pointer-events-none w-full justify-end",
                ),
                reset_on_submit=True,
                on_submit=AIState.send_message,
                class_name="flex flex-col gap-2",
            ),
            class_name="rounded-2xl bg-white w-full border border-gray-200 px-4 py-2 shadow-lg mx-auto z-10 focus-within:ring-blue-100 focus-within:ring-2 focus-within:border-blue-300 transition-all",
        ),
        class_name="px-6 mt-8 max-w-6xl mx-auto w-full",
    )


def welcome_cards() -> rx.Component:
    """Welcome cards with sample questions."""
    return rx.el.div(
        rx.el.div(
            rx.el.h2(
                "🤖 AI 센서 인사이트",
                class_name="text-2xl font-bold text-gray-800 mb-2",
            ),
            rx.el.p(
                "자연어로 센서 데이터를 질의하고 실시간 인사이트를 받아보세요",
                class_name="text-gray-600 mb-6",
            ),
            class_name="text-center mb-8",
        ),
        rx.el.div(
            welcome_card(
                "📊 현재 상태",
                "D101 센서 현재 상태는?",
                "현재 센서 값, QC 상태, 최근 트렌드를 확인합니다",
            ),
            welcome_card(
                "⚠️ 이상 탐지",
                "경고 상태인 센서 있어?",
                "QC 규칙을 기반으로 이상 센서를 찾아줍니다",
            ),
            welcome_card(
                "📈 트렌드 분석",
                "어제와 비교해서 어떤 센서가 많이 변했어?",
                "시간 기반 변화량 분석 및 비교를 제공합니다",
            ),
            welcome_card(
                "🎯 종합 진단",
                "전체 시스템 상태 요약해줘",
                "모든 센서의 종합적인 상태 분석을 제공합니다",
            ),
            class_name="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-6xl mx-auto w-full auto-rows-fr",
        ),
        class_name="flex flex-col items-center justify-start min-h-[600px] p-6 pt-8",
    )


def welcome_card(icon_title: str, question: str, description: str) -> rx.Component:
    """Individual welcome card component."""
    return rx.el.div(
        rx.el.div(
            rx.el.h3(
                icon_title,
                class_name="font-semibold text-gray-800 mb-2 text-sm",
            ),
            rx.el.p(
                f'"{question}"',
                class_name="text-blue-600 font-medium mb-2",
            ),
            rx.el.p(
                description,
                class_name="text-gray-500 text-xs",
            ),
        ),
        class_name="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md hover:border-blue-200 transition-all cursor-pointer min-h-[120px] flex flex-col justify-center",
        on_click=lambda: AIState.send_message({"message": question}),
    )


@rx.page("/ai", title="AI 센서 인사이트 - edgeEX Dashboard")
def ai_insights_page() -> rx.Component:
    """AI insights page with chat interface."""
    return shell(
        rx.el.div(
            chat_interface(),
            # Load initial sensor data on page mount
            on_mount=AIState.load_initial_sensor_data
        ),
        active_route="/ai"
    )
