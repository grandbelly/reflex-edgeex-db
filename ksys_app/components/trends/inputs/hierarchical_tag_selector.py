"""
Hierarchical Tag Selector Component
Station → System → Tag 3-tier selector with search
"""
import reflex as rx
from typing import List, Dict, Optional


def hierarchical_tag_selector(
    state,
    on_station_change=None,
    on_system_change=None,
    on_tag_select=None,
    max_selections: int = 5,
) -> rx.Component:
    """
    Hierarchical tag selector with Station/System/Tag filtering

    Args:
        state: State object with tag-related variables
        on_station_change: Handler for station selection
        on_system_change: Handler for system selection
        on_tag_select: Handler for tag selection
        max_selections: Maximum selectable tags

    Returns:
        Hierarchical selector component
    """
    return rx.vstack(
        # Header with count
        rx.hstack(
            rx.text(
                "Sensor Selection",
                size="3",
                weight="bold",
                color=rx.color("slate", 12),
            ),
            rx.badge(
                rx.text(
                    rx.cond(
                        state.selected_tags.length() > 0,
                        f"{state.selected_tags.length()}/{max_selections} selected",
                        "No tags selected"
                    ),
                    size="1",
                ),
                color_scheme="blue",
                variant="soft",
            ),
            spacing="2",
            width="100%",
            justify="between",
        ),

        # Station selector (Level 1)
        rx.vstack(
            rx.text(
                "Station",
                size="2",
                weight="medium",
                color=rx.color("slate", 11),
            ),
            rx.radio_group(
                ["ALL", "S01", "S02"],
                value=state.selected_station,
                on_change=on_station_change,
                direction="row",
                size="2",
            ),
            spacing="1",
            width="100%",
        ),

        # System selector (Level 2)
        rx.vstack(
            rx.text(
                "System Group",
                size="2",
                weight="medium",
                color=rx.color("slate", 11),
            ),
            rx.select(
                state.available_systems,
                placeholder="Select system group",
                value=state.selected_system,
                on_change=on_system_change,
                size="2",
                variant="soft",
                width="100%",
            ),
            spacing="1",
            width="100%",
        ),

        # Search box
        rx.vstack(
            rx.text(
                "Search Tags",
                size="2",
                weight="medium",
                color=rx.color("slate", 11),
            ),
            rx.input(
                placeholder="Type to search tags...",
                value=state.tag_search_query,
                on_change=state.set_tag_search_query,
                size="2",
                width="100%",
                radius="medium",
            ),
            spacing="1",
            width="100%",
        ),

        # Tag list with grouping (Level 3)
        rx.scroll_area(
            rx.vstack(
                # Show filtered tag count
                rx.hstack(
                    rx.text(
                        f"Available Tags ({state.filtered_tags.length()})",
                        size="1",
                        color=rx.color("slate", 10),
                    ),
                    rx.cond(
                        state.selected_system != "ALL",
                        rx.badge(
                            state.selected_system,
                            variant="outline",
                            size="1",
                        ),
                        rx.text(""),
                    ),
                    spacing="2",
                ),

                # Tag checkboxes
                rx.vstack(
                    rx.foreach(
                        state.filtered_tags,
                        lambda tag: rx.hstack(
                            rx.checkbox(
                                checked=state.is_tag_selected(tag),
                                on_change=lambda checked: on_tag_select(tag, checked),
                                size="1",
                                disabled=rx.cond(
                                    ~state.is_tag_selected(tag) &
                                    (state.selected_tags.length() >= max_selections),
                                    True,
                                    False
                                ),
                            ),
                            rx.text(
                                tag,
                                size="1",
                                color=rx.cond(
                                    state.is_tag_selected(tag),
                                    rx.color("blue", 11),
                                    rx.color("slate", 11)
                                ),
                                weight=rx.cond(
                                    state.is_tag_selected(tag),
                                    "medium",
                                    "regular"
                                ),
                            ),
                            spacing="2",
                            align="center",
                            width="100%",
                        ),
                    ),
                    spacing="1",
                    width="100%",
                ),
            ),
            height="300px",
            scrollbars="vertical",
            width="100%",
        ),

        # Selected tags display
        rx.cond(
            state.selected_tags.length() > 0,
            rx.vstack(
                rx.divider(),
                rx.text(
                    "Selected Tags",
                    size="2",
                    weight="medium",
                    color=rx.color("slate", 11),
                ),
                rx.flex(
                    rx.foreach(
                        state.selected_tags,
                        lambda tag: rx.badge(
                            rx.hstack(
                                rx.text(tag, size="1"),
                                rx.icon(
                                    "x",
                                    size=12,
                                    cursor="pointer",
                                    on_click=lambda: state.remove_selected_tag(tag),
                                ),
                                spacing="1",
                                align="center",
                            ),
                            color_scheme="blue",
                            variant="soft",
                            size="2",
                        ),
                    ),
                    wrap="wrap",
                    spacing="2",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            rx.text(""),  # Empty when no tags selected
        ),

        # Quick select buttons
        rx.hstack(
            rx.button(
                "Clear All",
                on_click=state.clear_selected_tags,
                size="1",
                variant="outline",
                color_scheme="gray",
                disabled=state.selected_tags.length() == 0,
            ),
            rx.button(
                f"Select Top {min(5, state.filtered_tags.length())}",
                on_click=state.select_top_tags,
                size="1",
                variant="outline",
                color_scheme="blue",
                disabled=state.selected_tags.length() >= max_selections,
            ),
            spacing="2",
            width="100%",
            justify="between",
        ),

        spacing="3",
        width="100%",
        padding="4",
        border=f"1px solid {rx.color('slate', 6)}",
        border_radius="8px",
        background=rx.color("slate", 2),
    )


def compact_tag_selector(
    state,
    on_change=None,
    placeholder: str = "Select tags...",
) -> rx.Component:
    """
    Compact tag selector for inline use (e.g., in toolbar)

    Args:
        state: State with tag variables
        on_change: Handler for tag selection
        placeholder: Placeholder text

    Returns:
        Compact selector component
    """
    return rx.popover(
        rx.popover.trigger(
            rx.button(
                rx.hstack(
                    rx.icon("filter", size=16),
                    rx.text(
                        rx.cond(
                            state.selected_tags.length() > 0,
                            f"{state.selected_tags.length()} tags",
                            placeholder
                        ),
                        size="2",
                    ),
                    rx.cond(
                        state.selected_tags.length() > 0,
                        rx.badge(
                            state.selected_station,
                            variant="soft",
                            size="1",
                        ),
                        rx.text(""),
                    ),
                    spacing="2",
                ),
                variant="soft",
                size="2",
            ),
        ),
        rx.popover.content(
            hierarchical_tag_selector(
                state=state,
                on_station_change=on_change,
                on_system_change=on_change,
                on_tag_select=on_change,
            ),
            width="400px",
        ),
    )