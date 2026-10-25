"""
Apple-mode Dual-Theme Component Library (`edgeex_app/design_system/am.py`).

설계 근거: docs/02-design/features/design-optimization.design.html §4
- 모든 표면/보더/텍스트/상태 색상은 `assets/styles.css`에 선언된 `--am-*` CSS 변수를 참조.
- `<html class="dark">` 토글(next-themes)과 동시에 라이트/다크 자동 전환.
- 5종 공용 컴포넌트:
  1. `am_card(*children, raised=False, **props)`
  2. `am_badge(label, severity="info", **props)`
  3. `am_button(label, variant="primary", on_click=None, icon=None, **props)`
  4. `am_search(placeholder="", value=None, on_change=None, **props)`
  5. `am_kpi_tile(label, value, unit=None, status="normal", delta=None, subtitle=None, icon=None, **props)`
"""
from __future__ import annotations

from typing import Any, Optional
import reflex as rx


_SEVERITY_TOKEN_MAP = {
    "info": "--am-info",
    "normal": "--am-success",
    "success": "--am-success",
    "good": "--am-success",
    "warning": "--am-warning",
    "uncertain": "--am-warning",
    "error": "--am-error",
    "alarm": "--am-error",
    "critical": "--am-error",
    "bad": "--am-error",
}


def am_card(*children: rx.Component, raised: bool = False, **props: Any) -> rx.Component:
    """듀얼 테마 카드 래퍼 (`var(--am-card)` / `var(--am-card-2)`)."""
    bg = props.pop("bg", props.pop("background", "var(--am-card-2)" if raised else "var(--am-card)"))
    border = props.pop("border", "1px solid var(--am-border)")
    border_radius = props.pop("border_radius", "var(--am-r-card)")
    padding = props.pop("padding", "1.25rem")
    width = props.pop("width", "100%")
    box_shadow = props.pop(
        "box_shadow",
        "0 4px 16px rgba(0, 0, 0, 0.06)" if raised else "0 1px 4px rgba(0, 0, 0, 0.03)",
    )
    return rx.box(
        *children,
        background=bg,
        border=border,
        border_radius=border_radius,
        padding=padding,
        width=width,
        box_shadow=box_shadow,
        transition="background-color var(--am-dur) var(--am-ease), border-color var(--am-dur) var(--am-ease)",
        **props,
    )


def am_badge(label: Any, severity: str = "info", **props: Any) -> rx.Component:
    """SCADA 심각도/품질 알약 배지 (`severity` ∈ {info, success, warning, error, alarm})."""
    token = _SEVERITY_TOKEN_MAP.get(str(severity).lower(), "--am-info")
    color_var = f"var({token})"
    bg_var = f"color-mix(in srgb, {color_var} 14%, transparent)"
    border_var = f"1px solid color-mix(in srgb, {color_var} 32%, transparent)"

    return rx.box(
        rx.text(
            label,
            size="1",
            weight="bold",
            style={
                "color": color_var,
                "font_family": "var(--am-font-mono)",
                "letter_spacing": "0.02em",
            },
        ),
        display="inline-flex",
        align_items="center",
        padding="2px 10px",
        border_radius="var(--am-r-pill)",
        background=bg_var,
        border=border_var,
        **props,
    )


def am_button(
    label: Any,
    variant: str = "primary",
    on_click: Any = None,
    icon: Optional[str] = None,
    **props: Any,
) -> rx.Component:
    """듀얼 테마 표준 버튼 (`primary` | `secondary` | `ghost`)."""
    variant_styles = {
        "primary": {
            "background": "var(--am-accent)",
            "color": "#ffffff",
            "border": "1px solid transparent",
        },
        "secondary": {
            "background": "var(--am-card-2)",
            "color": "var(--am-text)",
            "border": "1px solid var(--am-border-strong)",
        },
        "ghost": {
            "background": "transparent",
            "color": "var(--am-text)",
            "border": "1px solid transparent",
        },
    }
    st = dict(variant_styles.get(variant, variant_styles["primary"]))
    st["cursor"] = "pointer"
    st["border_radius"] = "var(--am-r-lg)"
    st["transition"] = "all 0.2s var(--am-ease)"

    user_style = props.pop("style", {})
    if isinstance(user_style, dict):
        st.update(user_style)

    content = (
        rx.hstack(rx.icon(icon, size=16), rx.text(label, size="2", weight="medium"), spacing="2", align="center")
        if icon
        else rx.text(label, size="2", weight="medium")
    )

    return rx.button(
        content,
        on_click=on_click,
        style=st,
        **props,
    )


def am_search(
    placeholder: str = "검색...",
    value: Any = None,
    on_change: Any = None,
    **props: Any,
) -> rx.Component:
    """좌측 검색 아이콘 + `--am-focus` 포커스 링을 갖춘 검색 입력창."""
    input_kwargs: dict[str, Any] = {
        "placeholder": placeholder,
        "width": "100%",
        "style": {
            "background": "var(--am-select)",
            "color": "var(--am-text)",
            "border": "1px solid var(--am-border-strong)",
            "border_radius": "var(--am-r-input)",
            "outline_color": "var(--am-focus)",
        },
    }
    if value is not None:
        input_kwargs["value"] = value
    if on_change is not None:
        input_kwargs["on_change"] = on_change
    input_kwargs.update(props)

    return rx.hstack(
        rx.icon("search", size=16, color="var(--am-muted)"),
        rx.input(**input_kwargs),
        align="center",
        spacing="2",
        width="100%",
    )


def am_kpi_tile(
    label: Any,
    value: Any,
    unit: Any = None,
    status: str = "normal",
    delta: Any = None,
    subtitle: Any = None,
    icon: Optional[str] = None,
    **props: Any,
) -> rx.Component:
    """단일화된 KPI 타일 컴포넌트."""
    status_token = _SEVERITY_TOKEN_MAP.get(str(status).lower(), "--am-success")
    dot_color = f"var({status_token})"

    header_items = [
        rx.hstack(
            rx.box(
                width="8px",
                height="8px",
                border_radius="50%",
                background=dot_color,
            ),
            rx.text(
                label,
                size="2",
                weight="medium",
                style={"color": "var(--am-muted)"},
            ),
            spacing="2",
            align="center",
        ),
        rx.spacer(),
    ]
    if icon:
        header_items.append(rx.icon(icon, size=18, color="var(--am-muted)"))

    value_row_items = [
        rx.text(
            value,
            size="6",
            weight="bold",
            class_name="ks-readout",
            style={
                "color": "var(--am-text)",
                "font_family": "var(--am-font-mono)",
            },
        ),
    ]
    if unit is not None:
        value_row_items.append(
            rx.text(
                unit,
                size="2",
                weight="medium",
                style={"color": "var(--am-muted)"},
            )
        )
    if delta is not None:
        value_row_items.append(
            rx.spacer(),
        )
        value_row_items.append(
            am_badge(delta, severity=status)
        )

    body_items = [
        rx.hstack(*header_items, width="100%", align="center"),
        rx.hstack(*value_row_items, align="baseline", spacing="2", width="100%"),
    ]
    if subtitle is not None:
        body_items.append(
            rx.text(
                subtitle,
                size="1",
                style={"color": "var(--am-muted-2)"},
            )
        )

    return am_card(
        rx.vstack(*body_items, spacing="2", align="start", width="100%"),
        raised=True,
        **props,
    )


__all__ = [
    "am_card",
    "am_badge",
    "am_button",
    "am_search",
    "am_kpi_tile",
]
