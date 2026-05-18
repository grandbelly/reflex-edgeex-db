"""
Enhanced Alarms State with Station/System filtering
Based on TagHierarchyState for hierarchical filtering
"""
import reflex as rx
from typing import List, Dict, Any, Optional
from reflex.utils import console
from datetime import datetime

from ksys_app.db_orm import get_async_session
from ksys_app.services.alarm_service import AlarmService
from .tag_hierarchy_state import TagHierarchyState


class AlarmsEnhancedState(TagHierarchyState):
    """Enhanced alarm state with Station/System filtering"""

    # Data storage
    alarms: List[Dict] = []

    # Statistics - individual fields for Reflex reactivity
    stat_total: int = 0
    stat_critical: int = 0
    stat_warning: int = 0
    stat_info: int = 0
    stat_unacknowledged: int = 0

    # ISA-18.2 Priority Statistics
    stat_priority_1_low: int = 0        # Priority 1: Advisory (Level 1-2)
    stat_priority_2_medium: int = 0     # Priority 2: Caution (Level 3)
    stat_priority_3_high: int = 0       # Priority 3: Warning (Level 4)
    stat_priority_4_critical: int = 0   # Priority 4: Emergency (Level 5)

    # UI control
    loading: bool = False
    error_message: str = ""
    last_update: str = ""
    view_mode: str = "active"  # "active" or "history"

    # Filters
    selected_hours: int = 24  # 24 hours default (show recent ISA-18.2 alarms)
    show_acknowledged: bool = False  # ISA-18.2 Standard: Real-time view shows unacknowledged only
    search_query: str = ""
    severity_filter: str = "all"  # all, CRITICAL, WARNING, INFO
    status_filter: str = "all"  # all, UNACKNOWLEDGED, ACKNOWLEDGED

    # Pagination
    page: int = 1
    page_size: int = 20
    total_count: int = 0

    # Selection
    selected_alarms: List[str] = []  # List of event_ids

    # Sensor-level status (like AlarmRTState and Dashboard)
    all_sensors: List[Dict] = []
    total_sensors_count: int = 0
    normal_sensors_count: int = 0
    warning_sensors_count: int = 0
    critical_sensors_count: int = 0

    # =========================================================================
    # Computed Properties for Hierarchical Filtering
    # =========================================================================

    def parse_alarm_tag(self, tag_name: str) -> tuple[str, str, str]:
        """
        Parse tag name into station, system, tag components
        Example: S01_RAW_FLOW_IN_PV -> ('S01', 'RAW', 'FLOW_IN_PV')
        """
        if not tag_name:
            return ("", "", "")

        parts = tag_name.split('_')
        if len(parts) < 3:
            return (tag_name, "", "")

        station = parts[0]  # S01 or S02
        system = parts[1]   # RAW, BIO, etc.
        tag = '_'.join(parts[2:])  # Rest is the tag name

        return (station, system, tag)

    @rx.var(cache=True)
    def filtered_alarms(self) -> List[Dict]:
        """Filter alarms based on Station/System selection and other filters"""
        result = self.alarms

        # Station filter - using tag hierarchy selection
        if self.selected_station != "ALL":
            result = [
                a for a in result
                if self.parse_alarm_tag(a.get("tag_name", ""))[0] == self.selected_station
            ]

        # System filter - using tag hierarchy selection
        if self.selected_system != "ALL":
            result = [
                a for a in result
                if self.parse_alarm_tag(a.get("tag_name", ""))[1] == self.selected_system
            ]

        # Search filter
        if self.search_query:
            query = self.search_query.lower()
            result = [
                a for a in result
                if query in a.get("message", "").lower()
                or query in a.get("tag_name", "").lower()
                or query in a.get("cause", "").lower()
            ]

        # Severity filter
        if self.severity_filter != "all":
            severity_map = {
                "CRITICAL": 5,
                "WARNING": 3,
                "INFO": 2,
            }
            level = severity_map.get(self.severity_filter.upper())
            if level:
                result = [a for a in result if a.get("level") == level]

        # Status filter
        if self.status_filter == "UNACKNOWLEDGED":
            result = [a for a in result if not a.get("acknowledged", False)]
        elif self.status_filter == "ACKNOWLEDGED":
            result = [a for a in result if a.get("acknowledged", False)]

        # Legacy show_acknowledged filter
        if not self.show_acknowledged:
            result = [a for a in result if not a.get("acknowledged", False)]

        return result

    @rx.var
    def filtered_count(self) -> int:
        """Number of filtered alarms"""
        return len(self.filtered_alarms)

    @rx.var
    def has_next_page(self) -> bool:
        """Check if there's a next page"""
        return self.page * self.page_size < self.filtered_count

    @rx.var
    def has_prev_page(self) -> bool:
        """Check if there's a previous page"""
        return self.page > 1

    @rx.var
    def total_pages(self) -> int:
        """Calculate total pages"""
        if self.page_size == 0:
            return 1
        return (self.filtered_count + self.page_size - 1) // self.page_size

    @rx.var
    def paginated_alarms(self) -> List[Dict]:
        """Get paginated alarms for current page"""
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        return self.filtered_alarms[start:end]

    @rx.var
    def alarm_counts_by_station(self) -> Dict[str, int]:
        """Count alarms by station"""
        counts = {"S01": 0, "S02": 0}
        for alarm in self.alarms:
            station = self.parse_alarm_tag(alarm.get("tag_name", ""))[0]
            if station in counts:
                counts[station] += 1
        return counts

    @rx.var
    def alarm_counts_by_system(self) -> Dict[str, int]:
        """Count alarms by system for selected station"""
        counts = {}
        for alarm in self.alarms:
            station, system, _ = self.parse_alarm_tag(alarm.get("tag_name", ""))
            # Filter by selected station
            if self.selected_station != "ALL" and station != self.selected_station:
                continue
            if system:
                counts[system] = counts.get(system, 0) + 1
        return counts

    # =========================================================================
    # Event Handlers
    # =========================================================================

    @rx.event(background=True)
    async def initialize(self):
        """Initialize state and load data"""
        console.log("[AlarmsEnhanced] Initialize called")

        # Load tag hierarchy first
        if not self.is_hierarchy_loaded:
            yield AlarmsEnhancedState.load_tag_hierarchy

        # Then load alarms
        yield AlarmsEnhancedState.refresh

    @rx.event(background=True)
    async def refresh(self):
        """Load alarms data"""
        async with self:
            self.loading = True
            self.error_message = ""
            yield

        try:
            async with get_async_session() as session:
                service = AlarmService(session)

                if self.view_mode == "active":
                    # Load active alarms
                    alarms_data = await service.get_active_alarms_unified()
                else:
                    # Load history alarms
                    alarms_data = await service.get_history_alarms_unified(
                        hours=self.selected_hours,
                        include_acknowledged=self.show_acknowledged
                    )

            # Update time
            from datetime import datetime
            import pytz
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)

            async with self:
                self.alarms = alarms_data
                self.last_update = now.strftime("%H:%M:%S")

                # Update statistics
                if self.view_mode == "active":
                    self.stat_total = len(alarms_data)
                    self.stat_critical = sum(1 for a in alarms_data if a.get("level") == 5)
                    self.stat_warning = sum(1 for a in alarms_data if a.get("level") == 3)
                    self.stat_info = sum(1 for a in alarms_data if a.get("level") == 2)
                    self.stat_unacknowledged = sum(1 for a in alarms_data if not a.get("acknowledged"))

                    # Update ISA priority statistics
                    self.stat_priority_1_low = sum(1 for a in alarms_data if a.get("isa_priority") == 1)
                    self.stat_priority_2_medium = sum(1 for a in alarms_data if a.get("isa_priority") == 2)
                    self.stat_priority_3_high = sum(1 for a in alarms_data if a.get("isa_priority") == 3)
                    self.stat_priority_4_critical = sum(1 for a in alarms_data if a.get("isa_priority") == 4)

                    console.log(f"[AlarmsEnhanced] Loaded {self.stat_total} active alarms")
                else:
                    console.log(f"[AlarmsEnhanced] Loaded {len(alarms_data)} history alarms")

                self.loading = False
                self.page = 1  # Reset to first page
                yield

        except Exception as e:
            console.error(f"[AlarmsEnhanced] Error loading alarms: {e}")
            async with self:
                self.error_message = f"Failed to load alarms: {str(e)}"
                self.loading = False
                yield

    def set_view_mode(self, mode: str):
        """Switch between active and history view"""
        self.view_mode = mode
        self.page = 1
        return AlarmsEnhancedState.refresh()

    def set_hours_filter(self, hours: str):
        """Set hours filter for history view"""
        try:
            self.selected_hours = int(hours)
            return AlarmsEnhancedState.refresh()
        except ValueError:
            console.error(f"Invalid hours value: {hours}")

    def toggle_show_acknowledged(self):
        """Toggle show acknowledged alarms"""
        self.show_acknowledged = not self.show_acknowledged
        return AlarmsEnhancedState.refresh()

    def set_search_query(self, query: str):
        """Update search query"""
        self.search_query = query
        self.page = 1

    def set_severity_filter(self, severity: str):
        """Update severity filter"""
        self.severity_filter = severity
        self.page = 1

    def set_status_filter(self, status: str):
        """Update status filter"""
        self.status_filter = status
        self.page = 1

    def next_page(self):
        """Go to next page"""
        if self.has_next_page:
            self.page += 1

    def prev_page(self):
        """Go to previous page"""
        if self.has_prev_page:
            self.page -= 1

    def toggle_alarm_selection(self, event_id: str):
        """Toggle alarm selection"""
        if event_id in self.selected_alarms:
            self.selected_alarms = [id for id in self.selected_alarms if id != event_id]
        else:
            self.selected_alarms.append(event_id)

    @rx.event(background=True)
    async def acknowledge_selected(self):
        """Acknowledge selected alarms"""
        if not self.selected_alarms:
            return

        async with self:
            self.loading = True
            yield

        try:
            async with get_async_session() as session:
                service = AlarmService(session)
                for event_id in self.selected_alarms:
                    await service.acknowledge_alarm(event_id)

            async with self:
                self.selected_alarms = []
                yield

            # Refresh data
            yield AlarmsEnhancedState.refresh()

        except Exception as e:
            console.error(f"[AlarmsEnhanced] Error acknowledging alarms: {e}")
            async with self:
                self.error_message = f"Failed to acknowledge alarms: {str(e)}"
                self.loading = False
                yield

    # Override parent methods for Station/System selection
    @rx.event
    def set_selected_station(self, station: str):
        """Override to also reset page when station changes"""
        self.selected_station = station
        self.selected_system = "ALL"  # Reset system when station changes
        self.page = 1  # Reset to first page

    @rx.event
    def set_selected_system(self, system: str):
        """Override to also reset page when system changes"""
        self.selected_system = system
        self.page = 1  # Reset to first page