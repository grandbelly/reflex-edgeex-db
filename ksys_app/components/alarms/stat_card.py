"""
통계 카드 컴포넌트 - 알람 대시보드용
Light Mode 디자인
"""
import reflex as rx
from typing import Optional


def stat_card(
    title: str,
    value: int | str | rx.Var,
    icon: str,
    color: str = "gray",
    trend: Optional[str | rx.Var] = None,
) -> rx.Component:
    """
    통계 카드 컴포넌트

    Args:
        title: 카드 제목 (예: "Total", "Critical")
        value: 표시할 값 (숫자 또는 문자열)
        icon: Lucide 아이콘 이름
        color: 색상 테마 ("gray", "red", "orange", "blue", "green")
        trend: 트렌드 텍스트 (예: "+5%", "-2%")

    Returns:
        통계 카드 컴포넌트
    """

    # Color schemes for Light Mode
    color_schemes = {
        "gray": {"icon_bg": "#192D40", "icon_color": "#8DA2C0"},
        "red": {"icon_bg": "#fef2f2", "icon_color": "#ef4444"},
        "orange": {"icon_bg": "#fff7ed", "icon_color": "#f97316"},
        "blue": {"icon_bg": "rgba(77,163,255,0.10)", "icon_color": "#3b82f6"},
        "green": {"icon_bg": "rgba(54,226,192,0.10)", "icon_color": "#10b981"},
    }

    scheme = color_schemes.get(color, color_schemes["gray"])

    return rx.card(
        rx.vstack(
            # Icon + Trend row
            rx.flex(
                rx.box(
                    rx.icon(icon, size=20, color=scheme["icon_color"]),
                    padding="2",
                    border_radius="md",
                    bg=scheme["icon_bg"],
                ),
                rx.spacer(),
                rx.cond(
                    trend is not None,
                    rx.text(trend, size="1", color="#8DA2C0", weight="medium"),
                    rx.box(),
                ),
                justify="between",
                width="100%",
            ),

            # Value
            rx.text(
                value,
                size="6",
                weight="bold",
                color="#E8F0FA",
            ),

            # Title
            rx.text(
                title,
                size="1",
                weight="medium",
                color="#8DA2C0",
            ),

            spacing="2",
            align="start",
        ),
        padding="4",
        size="2",
        bg="var(--ks-panel)",
        border="1px solid #22384E",
    )
