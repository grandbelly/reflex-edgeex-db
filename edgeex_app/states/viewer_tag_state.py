"""
Viewer Tag State - Tag visibility management for all screens
- Dashboard, Alarm, Trend, Model display control
- Display order management
- CRUD operations for viewer_tag table
"""
import reflex as rx
from typing import List, Dict, Any
from sqlalchemy import text
from reflex.utils import console

from edgeex_app.db_orm import get_async_session


class ViewerTagState(rx.State):
    """State for managing tag visibility across screens"""

    # Data
    tags: List[Dict] = []
    available_tags: List[str] = []  # Tags in influx_hist but not in viewer_tag

    # UI State
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    # Edit dialog
    show_edit_dialog: bool = False
    edit_tag: Dict = {}

    # Add dialog
    show_add_dialog: bool = False
    add_tag_name: str = ""

    # =========================================================================
    # LOAD DATA
    # =========================================================================

    @rx.event(background=True)
    async def load_tags(self):
        """Load all viewer tags from database"""
        async with self:
            self.is_loading = True
            self.error_message = ""
            yield

        try:
            async with get_async_session() as session:
                # Get viewer tags
                result = await session.execute(text("""
                    SELECT
                        tag_name,
                        display_order,
                        show_dashboard,
                        show_alarm,
                        show_trend,
                        show_model,
                        created_at,
                        updated_at
                    FROM viewer_tag
                    ORDER BY display_order, tag_name
                """))
                rows = result.mappings().all()

                tags = []
                for r in rows:
                    tags.append({
                        "tag_name": r["tag_name"],
                        "display_order": r["display_order"],
                        "show_dashboard": r["show_dashboard"],
                        "show_alarm": r["show_alarm"],
                        "show_trend": r["show_trend"],
                        "show_model": r["show_model"],
                        "created_at": str(r["created_at"])[:19] if r["created_at"] else "",
                        "updated_at": str(r["updated_at"])[:19] if r["updated_at"] else "",
                    })

                # Get available tags (in influx_hist but not in viewer_tag)
                avail_result = await session.execute(text("""
                    SELECT DISTINCT h.tag_name
                    FROM influx_hist h
                    LEFT JOIN viewer_tag v ON h.tag_name = v.tag_name
                    WHERE v.tag_name IS NULL
                    AND h.ts > NOW() - INTERVAL '7 days'
                    ORDER BY h.tag_name
                """))
                available = [r["tag_name"] for r in avail_result.mappings().all()]

                async with self:
                    self.tags = tags
                    self.available_tags = available
                    self.is_loading = False
                    yield

                console.info(f"Loaded {len(tags)} viewer tags, {len(available)} available to add")

        except Exception as e:
            console.error(f"Failed to load viewer tags: {e}")
            async with self:
                self.error_message = f"Failed to load: {str(e)}"
                self.is_loading = False
                yield

    # =========================================================================
    # TOGGLE VISIBILITY
    # =========================================================================

    @rx.event(background=True)
    async def toggle_dashboard(self, tag_name: str):
        """Toggle dashboard visibility for a tag"""
        try:
            async with get_async_session() as session:
                await session.execute(
                    text("UPDATE viewer_tag SET show_dashboard = NOT show_dashboard WHERE tag_name = :tag"),
                    {"tag": tag_name}
                )
                await session.commit()
            yield ViewerTagState.load_tags
        except Exception as e:
            console.error(f"Failed to toggle show_dashboard: {e}")
            async with self:
                self.error_message = f"Failed to update: {str(e)}"
                yield

    @rx.event(background=True)
    async def toggle_alarm(self, tag_name: str):
        """Toggle alarm visibility for a tag"""
        try:
            async with get_async_session() as session:
                await session.execute(
                    text("UPDATE viewer_tag SET show_alarm = NOT show_alarm WHERE tag_name = :tag"),
                    {"tag": tag_name}
                )
                await session.commit()
            yield ViewerTagState.load_tags
        except Exception as e:
            console.error(f"Failed to toggle show_alarm: {e}")
            async with self:
                self.error_message = f"Failed to update: {str(e)}"
                yield

    @rx.event(background=True)
    async def toggle_trend(self, tag_name: str):
        """Toggle trend visibility for a tag"""
        try:
            async with get_async_session() as session:
                await session.execute(
                    text("UPDATE viewer_tag SET show_trend = NOT show_trend WHERE tag_name = :tag"),
                    {"tag": tag_name}
                )
                await session.commit()
            yield ViewerTagState.load_tags
        except Exception as e:
            console.error(f"Failed to toggle show_trend: {e}")
            async with self:
                self.error_message = f"Failed to update: {str(e)}"
                yield

    @rx.event(background=True)
    async def toggle_model(self, tag_name: str):
        """Toggle model visibility for a tag"""
        try:
            async with get_async_session() as session:
                await session.execute(
                    text("UPDATE viewer_tag SET show_model = NOT show_model WHERE tag_name = :tag"),
                    {"tag": tag_name}
                )
                await session.commit()
            yield ViewerTagState.load_tags
        except Exception as e:
            console.error(f"Failed to toggle show_model: {e}")
            async with self:
                self.error_message = f"Failed to update: {str(e)}"
                yield

    # =========================================================================
    # UPDATE ORDER
    # =========================================================================

    @rx.event(background=True)
    async def update_order(self, tag_name: str, new_order: str):
        """Update display order for a tag"""
        try:
            order_int = int(new_order)
            async with get_async_session() as session:
                await session.execute(
                    text("UPDATE viewer_tag SET display_order = :order WHERE tag_name = :tag"),
                    {"order": order_int, "tag": tag_name}
                )
                await session.commit()

            yield ViewerTagState.load_tags

        except ValueError:
            async with self:
                self.error_message = "Order must be a number"
                yield
        except Exception as e:
            console.error(f"Failed to update order: {e}")
            async with self:
                self.error_message = f"Failed to update: {str(e)}"
                yield

    # =========================================================================
    # ADD TAG
    # =========================================================================

    def open_add_dialog(self):
        """Open add tag dialog"""
        self.show_add_dialog = True
        self.add_tag_name = ""

    def close_add_dialog(self):
        """Close add tag dialog"""
        self.show_add_dialog = False

    def set_add_tag_name(self, value: str):
        """Set tag name to add"""
        self.add_tag_name = value

    @rx.event(background=True)
    async def add_tag(self):
        """Add a new tag to viewer_tag"""
        tag_name = self.add_tag_name.strip()
        if not tag_name:
            async with self:
                self.error_message = "Tag name is required"
                yield
            return

        try:
            async with get_async_session() as session:
                # Get max order
                result = await session.execute(text(
                    "SELECT COALESCE(MAX(display_order), 0) + 10 as next_order FROM viewer_tag"
                ))
                next_order = result.scalar()

                await session.execute(
                    text("""
                        INSERT INTO viewer_tag (tag_name, display_order, show_dashboard, show_alarm, show_trend, show_model)
                        VALUES (:tag, :order, true, true, true, true)
                        ON CONFLICT (tag_name) DO NOTHING
                    """),
                    {"tag": tag_name, "order": next_order}
                )
                await session.commit()

            async with self:
                self.show_add_dialog = False
                self.success_message = f"Added tag: {tag_name}"
                yield

            yield ViewerTagState.load_tags

        except Exception as e:
            console.error(f"Failed to add tag: {e}")
            async with self:
                self.error_message = f"Failed to add: {str(e)}"
                yield

    # =========================================================================
    # DELETE TAG
    # =========================================================================

    @rx.event(background=True)
    async def delete_tag(self, tag_name: str):
        """Delete a tag from viewer_tag"""
        try:
            async with get_async_session() as session:
                await session.execute(
                    text("DELETE FROM viewer_tag WHERE tag_name = :tag"),
                    {"tag": tag_name}
                )
                await session.commit()

            async with self:
                self.success_message = f"Deleted tag: {tag_name}"
                yield

            yield ViewerTagState.load_tags

        except Exception as e:
            console.error(f"Failed to delete tag: {e}")
            async with self:
                self.error_message = f"Failed to delete: {str(e)}"
                yield

    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================

    @rx.event(background=True)
    async def show_all_dashboard(self):
        """Show all tags on dashboard"""
        try:
            async with get_async_session() as session:
                await session.execute(
                    text("UPDATE viewer_tag SET show_dashboard = true"),
                )
                await session.commit()
            yield ViewerTagState.load_tags
        except Exception as e:
            console.error(f"Failed bulk update show_dashboard: {e}")
            async with self:
                self.error_message = f"Failed: {str(e)}"
                yield

    @rx.event(background=True)
    async def hide_all_dashboard(self):
        """Hide all tags from dashboard"""
        try:
            async with get_async_session() as session:
                await session.execute(
                    text("UPDATE viewer_tag SET show_dashboard = false"),
                )
                await session.commit()
            yield ViewerTagState.load_tags
        except Exception as e:
            console.error(f"Failed bulk update show_dashboard: {e}")
            async with self:
                self.error_message = f"Failed: {str(e)}"
                yield

    # =========================================================================
    # CLEAR MESSAGES
    # =========================================================================

    def clear_messages(self):
        """Clear error and success messages"""
        self.error_message = ""
        self.success_message = ""
