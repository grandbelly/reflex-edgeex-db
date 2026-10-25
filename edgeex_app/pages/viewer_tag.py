"""
Viewer Tag Engineering Page

Manage tag visibility across screens:
- Dashboard, Alarm, Trend, Model display control
- Display order management
- Add/Delete tags from viewer_tag table
"""

import reflex as rx
from ..states.viewer_tag_state import ViewerTagState


def tag_table() -> rx.Component:
    """Table of viewer tags with visibility toggles"""
    return rx.vstack(
        rx.hstack(
            rx.heading("Viewer Tags", size="5"),
            rx.spacer(),
            rx.button(
                rx.icon("plus", size=16),
                "Add Tag",
                on_click=ViewerTagState.open_add_dialog,
                size="2",
                color_scheme="green",
            ),
            rx.button(
                rx.icon("refresh-cw", size=16),
                "Refresh",
                on_click=ViewerTagState.load_tags,
                loading=ViewerTagState.is_loading,
                size="2",
                variant="soft",
            ),
            spacing="2",
            width="100%",
            align="center",
        ),

        # Error/Success messages
        rx.cond(
            ViewerTagState.error_message,
            rx.callout(
                ViewerTagState.error_message,
                color_scheme="red",
                icon="triangle-alert",
            ),
        ),
        rx.cond(
            ViewerTagState.success_message,
            rx.callout(
                ViewerTagState.success_message,
                color_scheme="green",
                icon="circle-check",
            ),
        ),

        # Tags table
        rx.cond(
            ViewerTagState.tags.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Order", width="60px"),
                        rx.table.column_header_cell("Tag Name"),
                        rx.table.column_header_cell("Dashboard", width="90px"),
                        rx.table.column_header_cell("Alarm", width="80px"),
                        rx.table.column_header_cell("Trend", width="80px"),
                        rx.table.column_header_cell("Model", width="80px"),
                        rx.table.column_header_cell("Actions", width="80px"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        ViewerTagState.tags,
                        lambda tag: rx.table.row(
                            # Display Order
                            rx.table.cell(
                                rx.input(
                                    value=rx.Var.create(tag["display_order"]).to(str),
                                    on_blur=lambda e, t=tag: ViewerTagState.update_order(t["tag_name"], e),
                                    width="50px",
                                    size="1",
                                ),
                            ),
                            # Tag Name
                            rx.table.cell(
                                rx.text(tag["tag_name"], weight="medium"),
                            ),
                            # Dashboard toggle
                            rx.table.cell(
                                rx.switch(
                                    checked=tag["show_dashboard"],
                                    on_change=lambda _, t=tag: ViewerTagState.toggle_dashboard(t["tag_name"]),
                                    size="1",
                                ),
                            ),
                            # Alarm toggle
                            rx.table.cell(
                                rx.switch(
                                    checked=tag["show_alarm"],
                                    on_change=lambda _, t=tag: ViewerTagState.toggle_alarm(t["tag_name"]),
                                    size="1",
                                ),
                            ),
                            # Trend toggle
                            rx.table.cell(
                                rx.switch(
                                    checked=tag["show_trend"],
                                    on_change=lambda _, t=tag: ViewerTagState.toggle_trend(t["tag_name"]),
                                    size="1",
                                ),
                            ),
                            # Model toggle
                            rx.table.cell(
                                rx.switch(
                                    checked=tag["show_model"],
                                    on_change=lambda _, t=tag: ViewerTagState.toggle_model(t["tag_name"]),
                                    size="1",
                                ),
                            ),
                            # Actions
                            rx.table.cell(
                                rx.button(
                                    rx.icon("trash-2", size=14),
                                    on_click=lambda t=tag: ViewerTagState.delete_tag(t["tag_name"]),
                                    size="1",
                                    variant="ghost",
                                    color_scheme="red",
                                ),
                            ),
                        ),
                    ),
                ),
                width="100%",
            ),
            rx.text("No tags configured. Click 'Add Tag' to start.", color="gray"),
        ),

        spacing="4",
        width="100%",
    )


def bulk_actions() -> rx.Component:
    """Bulk action buttons"""
    return rx.card(
        rx.vstack(
            rx.heading("Bulk Actions", size="4"),
            rx.text("Quick actions for all tags", size="2", color="gray"),

            rx.hstack(
                rx.text("Dashboard:", weight="medium", width="100px"),
                rx.button(
                    "Show All",
                    on_click=ViewerTagState.show_all_dashboard,
                    size="1",
                    variant="soft",
                    color_scheme="green",
                ),
                rx.button(
                    "Hide All",
                    on_click=ViewerTagState.hide_all_dashboard,
                    size="1",
                    variant="soft",
                    color_scheme="red",
                ),
                spacing="2",
            ),

            spacing="3",
        ),
        padding="4",
    )


def available_tags_list() -> rx.Component:
    """List of available tags that can be added"""
    return rx.card(
        rx.vstack(
            rx.heading("Available Tags", size="4"),
            rx.text("Tags in influx_hist but not in viewer_tag", size="2", color="gray"),

            rx.cond(
                ViewerTagState.available_tags.length() > 0,
                rx.vstack(
                    rx.foreach(
                        ViewerTagState.available_tags,
                        lambda tag_name: rx.hstack(
                            rx.text(tag_name, size="2"),
                            rx.spacer(),
                            rx.button(
                                rx.icon("plus", size=12),
                                on_click=lambda t=tag_name: ViewerTagState.set_add_tag_name(t),
                                size="1",
                                variant="ghost",
                                color_scheme="green",
                            ),
                            width="100%",
                        ),
                    ),
                    spacing="1",
                    max_height="200px",
                    overflow="auto",
                ),
                rx.text("All tags are already configured", size="2", color="gray"),
            ),

            spacing="3",
        ),
        padding="4",
    )


def add_tag_dialog() -> rx.Component:
    """Dialog for adding a new tag"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Add Tag"),
            rx.dialog.description(
                "Enter a tag name to add to viewer_tag table"
            ),
            rx.vstack(
                rx.input(
                    placeholder="Enter tag name...",
                    value=ViewerTagState.add_tag_name,
                    on_change=ViewerTagState.set_add_tag_name,
                    width="100%",
                ),
                rx.cond(
                    ViewerTagState.available_tags.length() > 0,
                    rx.vstack(
                        rx.text("Or select from available:", size="2", color="gray"),
                        rx.select(
                            ViewerTagState.available_tags,
                            placeholder="Select a tag...",
                            on_change=ViewerTagState.set_add_tag_name,
                        ),
                        width="100%",
                        spacing="1",
                    ),
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            on_click=ViewerTagState.close_add_dialog,
                            variant="soft",
                            color_scheme="gray",
                        ),
                    ),
                    rx.button(
                        "Add Tag",
                        on_click=ViewerTagState.add_tag,
                        color_scheme="green",
                    ),
                    spacing="2",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                padding_top="4",
            ),
        ),
        open=ViewerTagState.show_add_dialog,
    )


@rx.page("/viewer-tag", on_load=ViewerTagState.load_tags)
def viewer_tag_page() -> rx.Component:
    """Viewer Tag Engineering page"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("eye", size=28),
                rx.heading("Tag Viewer Engineering", size="6"),
                spacing="3",
                align="center",
            ),
            rx.text(
                "Control which tags are visible on each screen (Dashboard, Alarm, Trend, Model)",
                color="gray",
            ),

            rx.grid(
                # Left: Main tag table
                rx.box(
                    tag_table(),
                    width="100%",
                ),

                # Right: Sidebar with bulk actions and available tags
                rx.vstack(
                    bulk_actions(),
                    available_tags_list(),
                    spacing="4",
                    width="100%",
                ),

                columns="3fr 1fr",
                spacing="6",
                width="100%",
            ),

            # Add dialog
            add_tag_dialog(),

            spacing="4",
            width="100%",
            max_width="1400px",
        ),
        padding="6",
    )
