"""Performance Charts - Visualize model performance metrics."""

import reflex as rx
from typing import Any


def performance_trend_chart(state_class: Any) -> rx.Component:
    """
    Chart showing MAE/RMSE/MAPE trends over time.

    Args:
        state_class: ModelPerformanceState class reference

    Returns:
        Recharts line chart component
    """
    return rx.cond(
        state_class.has_data,
        rx.recharts.line_chart(
            # X-axis (date)
            rx.recharts.x_axis(
                data_key="date",
                tick_formatter=rx.Var.create(
                    """(value) => {
                        const date = new Date(value);
                        return date.toLocaleDateString('ko-KR', {
                            month: 'short',
                            day: 'numeric'
                        });
                    }"""
                ),
            ),

            # Y-axis
            rx.recharts.y_axis(
                label={"value": "Error", "angle": -90, "position": "insideLeft"},
            ),

            # Tooltip
            rx.recharts.graphing_tooltip(
                content_style={
                    "backgroundColor": "#0E1724",
                    "border": "1px solid #22384E",
                    "borderRadius": "8px",
                },
                formatter=rx.Var.create(
                    """(value) => value ? value.toFixed(4) : 'N/A'"""
                ),
            ),

            # Legend
            rx.recharts.legend(),

            # Grid
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
                opacity=0.3,
            ),

            # MAE line
            rx.recharts.line(
                data_key="mae",
                stroke="#3b82f6",  # blue
                name="MAE",
                stroke_width=2,
                dot=True,
            ),

            # RMSE line
            rx.recharts.line(
                data_key="rmse",
                stroke="#ef4444",  # red
                name="RMSE",
                stroke_width=2,
                dot=True,
            ),

            # MAPE line
            rx.recharts.line(
                data_key="mape",
                stroke="#10b981",  # green
                name="MAPE",
                stroke_width=2,
                dot=True,
            ),

            data=state_class.chart_data,
            width="100%",
            height=400,
        ),
        rx.center(
            rx.vstack(
                rx.icon("line-chart", size=48, color="gray"),
                rx.text(
                    "성능 데이터가 없습니다.",
                    size="4",
                    color="gray",
                    weight="medium",
                ),
                spacing="3",
                align="center",
            ),
            height="400px",
        ),
    )


def model_comparison_chart(state_class: Any) -> rx.Component:
    """
    Bar chart comparing model types by average MAE.

    Args:
        state_class: ModelPerformanceState class reference

    Returns:
        Recharts bar chart component
    """
    return rx.cond(
        state_class.model_comparison.length() > 0,
        rx.recharts.bar_chart(
            # X-axis
            rx.recharts.x_axis(
                data_key="model_type",
            ),

            # Y-axis
            rx.recharts.y_axis(
                label={"value": "Average MAE", "angle": -90, "position": "insideLeft"},
            ),

            # Tooltip
            rx.recharts.graphing_tooltip(
                content_style={
                    "backgroundColor": "#0E1724",
                    "border": "1px solid #22384E",
                    "borderRadius": "8px",
                },
                formatter=rx.Var.create(
                    """(value) => value ? value.toFixed(4) : 'N/A'"""
                ),
            ),

            # Legend
            rx.recharts.legend(),

            # Grid
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
                opacity=0.3,
            ),

            # MAE bar - Brand Purple (Design System)
            rx.recharts.bar(
                data_key="avg_mae",
                fill=rx.color("purple", 9),
                name="Average MAE",
                radius=[8, 8, 0, 0],
            ),

            data=state_class.model_comparison,
            width="100%",
            height=300,
        ),
        rx.center(
            rx.vstack(
                rx.icon("bar-chart", size=48, color=rx.color("gray", 7)),
                rx.text(
                    "모델 타입별 비교 데이터가 없습니다.",
                    size="4",
                    color="gray",
                    weight="medium",
                ),
                rx.callout.root(
                    rx.callout.icon(rx.icon("info")),
                    rx.vstack(
                        rx.text(
                            "데이터가 표시되지 않는 이유:",
                            size="2",
                            weight="bold",
                        ),
                        rx.text(
                            "1. Training Wizard에서 아직 모델을 훈련하지 않았거나",
                            size="1",
                        ),
                        rx.text(
                            "2. 훈련된 모델의 평균 성능 데이터가 아직 집계되지 않았습니다.",
                            size="1",
                        ),
                        rx.text(
                            "Training Wizard에서 여러 모델을 훈련하면 타입별 평균 성능이 자동으로 표시됩니다.",
                            size="1",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    color_scheme="purple",
                    size="1",
                ),
                spacing="3",
                align="center",
                width="100%",
                max_width="600px",
            ),
            height="300px",
            padding="4",
        ),
    )


def drift_severity_chart(state_class: Any) -> rx.Component:
    """
    Chart showing drift severity over time.

    Args:
        state_class: ModelPerformanceState class reference

    Returns:
        Recharts area chart component
    """
    return rx.cond(
        state_class.drift_history.length() > 0,
        rx.recharts.area_chart(
            # X-axis
            rx.recharts.x_axis(
                data_key="detected_at",
                tick_formatter=rx.Var.create(
                    """(value) => {
                        const date = new Date(value);
                        return date.toLocaleDateString('ko-KR', {
                            month: 'short',
                            day: 'numeric'
                        });
                    }"""
                ),
            ),

            # Y-axis
            rx.recharts.y_axis(
                label={"value": "PSI Value", "angle": -90, "position": "insideLeft"},
            ),

            # Tooltip
            rx.recharts.graphing_tooltip(
                content_style={
                    "backgroundColor": "#0E1724",
                    "border": "1px solid #22384E",
                    "borderRadius": "8px",
                },
            ),

            # Legend
            rx.recharts.legend(),

            # Grid
            rx.recharts.cartesian_grid(
                stroke_dasharray="3 3",
                opacity=0.3,
            ),

            # Reference lines for severity thresholds
            rx.recharts.reference_line(
                y="0.1",
                stroke="var(--amber-9)",
                stroke_dasharray="3 3",
                label="Low",
            ),

            rx.recharts.reference_line(
                y="0.2",
                stroke="var(--red-9)",
                stroke_dasharray="3 3",
                label="High",
            ),

            # PSI area
            rx.recharts.area(
                data_key="psi_value",
                stroke="#f59e0b",
                fill="#f59e0b",
                fill_opacity=0.3,
                name="PSI Value",
            ),

            data=state_class.drift_history,
            width="100%",
            height=300,
        ),
        rx.center(
            rx.text("드리프트 데이터가 없습니다.", size="2", color="gray"),
            height="300px",
        ),
    )


def current_models_table(state_class: Any) -> rx.Component:
    """
    Table showing current active models.

    Args:
        state_class: ModelPerformanceState class reference

    Returns:
        Table component
    """
    return rx.cond(
        state_class.current_models.length() > 0,
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("모델 타입"),
                    rx.table.column_header_cell("버전"),
                    rx.table.column_header_cell("MAE"),
                    rx.table.column_header_cell("RMSE"),
                    rx.table.column_header_cell("학습 시간"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    state_class.current_models,
                    lambda model: rx.table.row(
                        rx.table.cell(
                            rx.badge(
                                model['model_type'],
                                color_scheme="blue",
                                variant="soft",
                            )
                        ),
                        rx.table.cell(
                            rx.text(model['version'], size="2")
                        ),
                        rx.table.cell(
                            rx.text(
                                rx.cond(
                                    model["mae"],
                                    model["mae"].to(str),
                                    "N/A"
                                ),
                                size="2",
                                weight="bold",
                            )
                        ),
                        rx.table.cell(
                            rx.text(
                                rx.cond(
                                    model["rmse"],
                                    model["rmse"].to(str),
                                    "N/A"
                                ),
                                size="2",
                            )
                        ),
                        rx.table.cell(
                            rx.text(
                                rx.cond(
                                    model["trained_at"],
                                    model["trained_at"],
                                    "N/A"
                                ),
                                size="2",
                                color="gray",
                            )
                        ),
                    ),
                ),
            ),
            variant="surface",
            size="2",
        ),
        rx.center(
            rx.text("활성 모델이 없습니다.", size="2", color="gray"),
            padding="4",
        ),
    )


def performance_summary_card(state_class: Any) -> rx.Component:
    """
    Summary card with key metrics.

    Args:
        state_class: ModelPerformanceState class reference

    Returns:
        Card component
    """
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("bar-chart-2", size=20, color="blue"),
                rx.heading("성능 요약", size="4"),
                spacing="2",
                align="center",
            ),

            rx.divider(),

            rx.grid(
                # Total models
                rx.box(
                    rx.vstack(
                        rx.text("총 모델 수", size="2", color="gray", weight="medium"),
                        rx.text(
                            state_class.total_predictions.to_string(),
                            size="6",
                            weight="bold",
                            color="blue",
                        ),
                        spacing="1",
                    ),
                ),

                # Average MAE
                rx.box(
                    rx.vstack(
                        rx.text("평균 MAE", size="2", color="gray", weight="medium"),
                        rx.text(
                            f"{state_class.avg_mae:.4f}",
                            size="6",
                            weight="bold",
                            color="green",
                        ),
                        spacing="1",
                    ),
                ),

                # Drift count
                rx.box(
                    rx.vstack(
                        rx.text("드리프트 감지", size="2", color="gray", weight="medium"),
                        rx.text(
                            state_class.drift_count.to_string(),
                            size="6",
                            weight="bold",
                            color=rx.cond(
                                state_class.drift_count > 3,
                                "red",
                                "amber"
                            ),
                        ),
                        spacing="1",
                    ),
                ),

                # Best model
                rx.box(
                    rx.vstack(
                        rx.text("최적 모델", size="2", color="gray", weight="medium"),
                        rx.badge(
                            state_class.best_model_type,
                            color_scheme="purple",
                            variant="soft",
                            size="3",
                        ),
                        spacing="1",
                    ),
                ),

                columns="4",
                spacing="4",
                width="100%",
            ),

            spacing="4",
            width="100%",
        ),
        size="2",
    )


def retraining_recommendation(state_class: Any) -> rx.Component:
    """
    Show retraining recommendation if needed.

    Args:
        state_class: ModelPerformanceState class reference

    Returns:
        Callout component
    """
    return rx.cond(
        state_class.needs_retraining,
        rx.callout.root(
            rx.callout.icon(
                rx.icon("triangle-alert"),
            ),
            rx.callout.text(
                rx.vstack(
                    rx.text(
                        "모델 재학습 권장",
                        weight="bold",
                        size="3",
                    ),
                    rx.text(
                        "성능 저하 또는 드리프트가 감지되었습니다. 모델 재학습을 권장합니다.",
                        size="2",
                    ),
                    rx.button(
                        rx.icon("refresh-cw", size=16),
                        "재학습 실행",
                        size="2",
                        variant="soft",
                        color_scheme="amber",
                    ),
                    spacing="2",
                    align="start",
                ),
            ),
            color_scheme="amber",
            size="2",
        ),
        rx.fragment(),
    )
def saved_models_table(state_class: Any) -> rx.Component:
    """
    Table showing all saved models with deployment options - REDESIGNED.

    Args:
        state_class: ModelPerformanceState class reference

    Returns:
        Table component with model list and deploy buttons
    """
    return rx.cond(
        state_class.saved_models,
        rx.box(
            rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("ID"),
                    rx.table.column_header_cell("모델 타입"),
                    rx.table.column_header_cell("버전"),
                    rx.table.column_header_cell("Train MAE"),
                    rx.table.column_header_cell("Val MAE"),
                    rx.table.column_header_cell("RMSE"),
                    rx.table.column_header_cell("생성 시간"),
                    rx.table.column_header_cell("상태"),
                    rx.table.column_header_cell("동작"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    state_class.saved_models,
                    lambda model: rx.table.row(
                        rx.table.cell(rx.text(model["model_id"], size="2", weight="medium")),
                        rx.table.cell(rx.badge(model["model_type"], color_scheme="blue", variant="soft")),
                        rx.table.cell(rx.text(model["version"], size="2", color="gray")),
                        rx.table.cell(
                            rx.text(
                                rx.cond(
                                    model["train_mae"].to(str) != "None",
                                    rx.cond(
                                        model["train_mae"] == 0.0,
                                        "0.00",
                                        model["train_mae"].to(str)
                                    ),
                                    "N/A"
                                ),
                                size="2",
                                color="blue"
                            )
                        ),
                        rx.table.cell(
                            rx.text(
                                rx.cond(
                                    model["validation_mae"].to(str) != "None",
                                    rx.cond(
                                        model["validation_mae"] == 0.0,
                                        "0.00",
                                        model["validation_mae"].to(str)
                                    ),
                                    "N/A"
                                ),
                                size="2",
                                color="purple",
                                weight="bold"
                            )
                        ),
                        rx.table.cell(
                            rx.text(
                                rx.cond(
                                    model["validation_rmse"].to(str) != "None",
                                    rx.cond(
                                        model["validation_rmse"] == 0.0,
                                        "0.00",
                                        model["validation_rmse"].to(str)
                                    ),
                                    "N/A"
                                ),
                                size="2"
                            )
                        ),
                        rx.table.cell(rx.text(rx.cond(model["created_at"], model["created_at"], "N/A"), size="1", color="gray")),
                        rx.table.cell(
                            rx.cond(
                                model["is_deployed"],
                                rx.badge(rx.hstack(rx.icon("circle", size=12), rx.text("배포 중"), spacing="1"), color_scheme="green", variant="soft"),
                                rx.badge("대기", color_scheme="gray", variant="soft"),
                            )
                        ),
                        rx.table.cell(
                            rx.hstack(
                                rx.cond(
                                    model["is_deployed"],
                                    rx.button(
                                        rx.icon("circle-x", size=16),
                                        "해제",
                                        size="1",
                                        variant="soft",
                                        color_scheme="gray",
                                        on_click=state_class.undeploy_model(model["model_id"])
                                    ),
                                    rx.button(
                                        rx.icon("play", size=16),
                                        "배포",
                                        size="1",
                                        variant="soft",
                                        color_scheme="green",
                                        on_click=state_class.deploy_model(model["model_id"])
                                    ),
                                ),
                                rx.button(
                                    rx.icon("trash-2", size=16),
                                    "삭제",
                                    size="1",
                                    variant="soft",
                                    color_scheme="red",
                                    on_click=state_class.set_selected_model_for_delete(model["model_id"])
                                ),
                                spacing="2",
                            )
                        ),
                    ),
                ),
            ),
            variant="surface",
            size="2",
            ),
            width="100%",
            overflow_x="auto",
        ),
        rx.center(
            rx.vstack(
                rx.icon("inbox", size=40, color="gray"),
                rx.text("저장된 모델이 없습니다", size="3", color="gray"),
                rx.text("Training Wizard에서 모델을 훈련하고 저장하세요", size="2", color="gray"),
                spacing="3",
                align="center",
            ),
            height="200px",
        ),
    )


# ORIGINAL saved_models_table function for reference
def _original_saved_models_table_BACKUP(state_class: Any) -> rx.Component:
    """BACKUP - Original implementation."""

    def model_row(model: rx.Var) -> rx.Component:
        """Single model row."""
        return rx.box(
            rx.hstack(
                # Model ID
                rx.text(
                    model["model_id"],
                    size="2",
                    weight="medium",
                    width="60px",
                ),

                # Model Type
                rx.badge(
                    model["model_type"],
                    color_scheme="blue",
                    variant="soft",
                    width="80px",
                ),

                # Version
                rx.text(
                    model["version"],
                    size="2",
                    color="gray",
                    width="60px",
                ),

                # Train MAE
                rx.text(
                    model["train_mae"],
                    size="2",
                    width="80px",
                ),

                # Validation MAE
                rx.text(
                    model["validation_mae"],
                    size="2",
                    color="gray",
                    width="100px",
                ),

                # Created At
                rx.text(
                    model["created_at"],
                    size="1",
                    color="gray",
                    width="150px",
                ),

                rx.spacer(),

                # Deployment Status
                rx.cond(
                    model["is_deployed"],
                    rx.badge(
                        "배포 중",
                        color_scheme="green",
                        variant="soft",
                    ),
                    rx.badge(
                        "대기",
                        color_scheme="gray",
                        variant="soft",
                    ),
                ),

                spacing="3",
                align="center",
                width="100%",
            ),
            padding="3",
            border_radius="md",
            _hover={
                "background": rx.color("gray", 2),
            },
        )

    return rx.cond(
        state_class.saved_models,
        rx.vstack(
            # Header
            rx.hstack(
                rx.text("ID", size="1", weight="bold", color="gray", width="60px"),
                rx.text("Type", size="1", weight="bold", color="gray", width="80px"),
                rx.text("Ver", size="1", weight="bold", color="gray", width="60px"),
                rx.text("Train MAE", size="1", weight="bold", color="gray", width="80px"),
                rx.text("Val MAE", size="1", weight="bold", color="gray", width="100px"),
                rx.text("Created", size="1", weight="bold", color="gray", width="150px"),
                rx.spacer(),
                rx.text("Status", size="1", weight="bold", color="gray", width="80px"),
                spacing="3",
                width="100%",
                padding_x="3",
                padding_y="2",
                border_bottom=f"1px solid {rx.color('gray', 4)}",
            ),

            # Model Rows
            rx.foreach(
                state_class.saved_models,
                model_row,
            ),

            spacing="1",
            width="100%",
        ),
        rx.center(
            rx.vstack(
                rx.icon("inbox", size=40, color="gray"),
                rx.text("저장된 모델이 없습니다", size="3", color="gray"),
                rx.text(
                    "Training Wizard에서 모델을 훈련하고 저장하세요",
                    size="2",
                    color="gray",
                ),
                spacing="3",
                align="center",
            ),
            height="200px",
        ),
    )


def deployed_model_info_card(state_class: Any) -> rx.Component:
    """Card showing currently deployed model information - REDESIGNED."""
    return rx.cond(
        state_class.has_deployed_model,
        rx.vstack(
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon("circle", size=16, color="green"),
                        rx.heading("현재 배포된 모델", size="4"),
                        rx.spacer(),
                        rx.badge(rx.hstack(rx.icon("activity", size=12), rx.text("실시간 예측 중"), spacing="1"), color_scheme="green", variant="soft"),
                        spacing="2", align="center", width="100%",
                    ),
                    rx.divider(),
                    rx.grid(
                        rx.vstack(rx.text("Model ID", size="1", color="gray", weight="medium"), rx.text(state_class.deployed_model_info["model_id"], size="4", weight="bold", color="blue"), spacing="1", align="start"),
                        rx.vstack(rx.text("모델 타입", size="1", color="gray", weight="medium"), rx.badge(state_class.deployed_model_info["model_type"], color_scheme="blue", variant="soft", size="3"), spacing="1", align="start"),
                        rx.vstack(rx.text("버전", size="1", color="gray", weight="medium"), rx.text(state_class.deployed_model_info["version"], size="3", weight="medium"), spacing="1", align="start"),
                        rx.vstack(rx.text("배포 시간", size="1", color="gray", weight="medium"), rx.text(rx.cond(state_class.deployed_model_info["deployed_at"], state_class.deployed_model_info["deployed_at"], "N/A"), size="2"), spacing="1", align="start"),
                        columns="4", spacing="4", width="100%",
                    ),
                    rx.divider(),
                    rx.vstack(
                        rx.text("성능 지표", size="2", weight="bold", color="gray"),
                        rx.grid(
                            rx.box(
                                rx.vstack(
                                    rx.text("Validation MAE", size="1", color="gray"),
                                    rx.text(
                                        rx.cond(
                                            state_class.deployed_model_info["validation_mae"].to(str) != "None",
                                            rx.cond(
                                                state_class.deployed_model_info["validation_mae"] == 0.0,
                                                "0.00",
                                                state_class.deployed_model_info["validation_mae"].to(str)
                                            ),
                                            "N/A"
                                        ),
                                        size="4",
                                        weight="bold",
                                        color="purple"
                                    ),
                                    spacing="1",
                                    align="center"
                                ),
                                padding="3",
                                border_radius="md",
                                bg="#192D40"
                            ),
                            rx.box(
                                rx.vstack(
                                    rx.text("RMSE", size="1", color="gray"),
                                    rx.text(
                                        rx.cond(
                                            state_class.deployed_model_info["validation_rmse"].to(str) != "None",
                                            rx.cond(
                                                state_class.deployed_model_info["validation_rmse"] == 0.0,
                                                "0.00",
                                                state_class.deployed_model_info["validation_rmse"].to(str)
                                            ),
                                            "N/A"
                                        ),
                                        size="4",
                                        weight="bold",
                                        color="green"
                                    ),
                                    spacing="1",
                                    align="center"
                                ),
                                padding="3",
                                border_radius="md",
                                bg="#192D40"
                            ),
                            rx.box(
                                rx.vstack(
                                    rx.text("MAPE", size="1", color="gray"),
                                    rx.text(
                                        rx.cond(
                                            state_class.deployed_model_info["validation_mape"].to(str) != "None",
                                            rx.cond(
                                                state_class.deployed_model_info["validation_mape"] == 0.0,
                                                "0.00%",
                                                state_class.deployed_model_info["validation_mape"].to(str) + "%"
                                            ),
                                            "N/A"
                                        ),
                                        size="4",
                                        weight="bold",
                                        color="amber"
                                    ),
                                    spacing="1",
                                    align="center"
                                ),
                                padding="3",
                                border_radius="md",
                                bg="#192D40"
                            ),
                            columns="3",
                            spacing="3",
                            width="100%",
                        ),
                        spacing="3", width="100%",
                    ),
                    spacing="4", width="100%",
                ),
                size="2",
                width="100%",
            ),
            # 🆕 NEW: Forecast Player Navigation Card
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon("circle-play", size=20, color="green"),
                        rx.heading("실시간 예측 결과", size="4"),
                        spacing="2",
                    ),
                    rx.callout.root(
                        rx.callout.icon(rx.icon("info")),
                        rx.callout.text(
                            "배포된 모델이 생성한 예측 결과를 실시간으로 확인할 수 있습니다. "
                            "과거 예측의 정확도 분석, 현재 예측값 모니터링, 미래 예측 시뮬레이션을 지원합니다."
                        ),
                        color_scheme="blue",
                        size="1",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon("trending-up", size=18),
                            rx.text("예측 결과 보기"),
                            spacing="2",
                        ),
                        on_click=state_class.navigate_to_forecast_player,
                        color_scheme="green",
                        size="3",
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),
                size="2",
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
        rx.callout.root(rx.callout.icon(rx.icon("info")), rx.callout.text("현재 배포된 모델이 없습니다. 저장된 모델 목록에서 모델을 선택하고 '배포' 버튼을 클릭하세요."), color_scheme="blue", size="2", width="100%"),
    )


