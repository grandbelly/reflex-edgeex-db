"""
Enhanced Dashboard Realtime State with Station/System Grouping
"""
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List
import reflex as rx
from reflex.utils import console

from ksys_app.states.base_state import BaseState
from ksys_app.states.tag_hierarchy_state import TagHierarchyState
from ksys_app.services.sensor_service import SensorService
from ksys_app.db_orm import get_async_session
from ksys_app.config.limits import UI_LIMITS


class DashboardRealtimeGroupedState(TagHierarchyState):
    """Enhanced real-time dashboard with Station/System grouping"""

    # Data (from parent)
    sensors: List[Dict] = []
    chart_data: Dict[str, List[Dict]] = {}

    # Forecast data
    forecast_data: Dict[str, Dict] = {}

    # Statistics
    normal_count: int = 0
    warning_count: int = 0
    critical_count: int = 0

    # Additional statistics for grouped view
    station_stats: Dict[str, Dict] = {}  # {station: {normal, warning, critical}}
    system_stats: Dict[str, Dict] = {}   # {system: {normal, warning, critical}}

    # UI State
    last_update: str = ""
    is_streaming: bool = False
    update_interval: int = 15

    # View preferences
    view_mode: str = "grouped"  # "grouped", "flat", "compact"
    expanded_sections: List[str] = []  # Track which sections are expanded
    show_critical_only: bool = False
    show_warnings_only: bool = False

    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================

    @rx.var
    def grouped_sensors(self) -> Dict[str, Dict[str, List[Dict]]]:
        """Group sensors by Station and System"""
        grouped = {}

        for sensor in self.filtered_sensors:
            tag_name = sensor.get("tag_name", "")
            parts = tag_name.split("_")

            if len(parts) >= 2:
                station = parts[0]
                system = parts[1]

                if station not in grouped:
                    grouped[station] = {}
                if system not in grouped[station]:
                    grouped[station][system] = []

                grouped[station][system].append(sensor)

        return grouped

    @rx.var
    def filtered_sensors(self) -> List[Dict]:
        """Filter sensors based on current selections"""
        result = self.sensors

        # Filter by station
        if self.selected_station != "ALL":
            result = [
                s for s in result
                if s.get("tag_name", "").startswith(self.selected_station)
            ]

        # Filter by system
        if self.selected_system != "ALL":
            result = [
                s for s in result
                if f"_{self.selected_system}_" in s.get("tag_name", "")
            ]

        # Filter by status
        if self.show_critical_only:
            result = [s for s in result if s.get("status") == "critical"]
        elif self.show_warnings_only:
            result = [s for s in result if s.get("status") == "warning"]

        # Filter by search query
        if self.tag_search_query:
            query = self.tag_search_query.upper()
            result = [
                s for s in result
                if query in s.get("tag_name", "").upper() or
                query in s.get("description", "").upper()
            ]

        return result

    @rx.var
    def sorted_sensors(self) -> List[Dict]:
        """Sort sensors by criticality and name"""
        status_order = {"critical": 0, "warning": 1, "normal": 2, "unknown": 3}

        return sorted(
            self.filtered_sensors,
            key=lambda s: (
                status_order.get(s.get("status", "unknown"), 3),
                s.get("tag_name", "")
            )
        )

    @rx.var
    def critical_sensors(self) -> List[Dict]:
        """Get only critical sensors"""
        return [s for s in self.sensors if s.get("status") == "critical"]

    @rx.var
    def warning_sensors(self) -> List[Dict]:
        """Get only warning sensors"""
        return [s for s in self.sensors if s.get("status") == "warning"]

    @rx.var
    def station_summary(self) -> List[Dict]:
        """Summary statistics by station"""
        summary = []
        for station in self.available_stations:
            if station == "ALL":
                continue

            stats = self.station_stats.get(station, {})
            total = stats.get("normal", 0) + stats.get("warning", 0) + stats.get("critical", 0)

            if total > 0:
                summary.append({
                    "station": station,
                    "total": total,
                    "normal": stats.get("normal", 0),
                    "warning": stats.get("warning", 0),
                    "critical": stats.get("critical", 0),
                    "critical_pct": round(100 * stats.get("critical", 0) / total, 1),
                    "health_score": round(100 * stats.get("normal", 0) / total, 1),
                })

        return sorted(summary, key=lambda x: x["critical"], reverse=True)

    @rx.var
    def system_summary(self) -> List[Dict]:
        """Summary statistics by system"""
        summary = []
        for system, count in self.system_tag_counts.items():
            stats = self.system_stats.get(system, {})
            total = stats.get("normal", 0) + stats.get("warning", 0) + stats.get("critical", 0)

            if total > 0:
                summary.append({
                    "system": system,
                    "total": total,
                    "normal": stats.get("normal", 0),
                    "warning": stats.get("warning", 0),
                    "critical": stats.get("critical", 0),
                    "critical_pct": round(100 * stats.get("critical", 0) / total, 1) if total > 0 else 0,
                })

        return sorted(summary, key=lambda x: x["critical"], reverse=True)

    # =========================================================================
    # STREAMING & DATA FETCHING
    # =========================================================================

    @rx.event(background=True)
    async def start_streaming_grouped(self):
        """Start streaming with grouped data"""
        # Load hierarchy first
        if not self.is_hierarchy_loaded:
            await self.load_tag_hierarchy()

        # Set initial state
        async with self:
            self.is_streaming = True
            self.last_update = "Initializing..."
            yield

        console.info(f"Grouped dashboard streaming started (interval: {self.update_interval}s)")

        # Initial load
        try:
            await asyncio.wait_for(
                self._fetch_grouped_data(),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            console.log("Initial data load timeout")
            async with self:
                self.last_update = "Initial load timeout"
                yield
        except Exception as e:
            console.error(f"Initial load error: {e}")
            async with self:
                snippet = str(e)[:UI_LIMITS.log_error_snippet_chars]
                self.last_update = f"Error: {snippet}"
                yield

        # Streaming loop
        while self.is_streaming:
            await asyncio.sleep(self.update_interval)
            try:
                await asyncio.wait_for(
                    self._fetch_grouped_data(),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                console.log("Update timeout, continuing...")
            except Exception as e:
                console.error(f"Update error: {e}")

    async def _fetch_grouped_data(self):
        """Fetch and group sensor data"""
        try:
            async with get_async_session() as session:
                service = SensorService(session)

                # Get sensor data with status
                sensors_with_status = await service.get_sensors_with_status()

                # Calculate statistics
                station_stats = {}
                system_stats = {}
                normal = warning = critical = 0

                for sensor in sensors_with_status:
                    # Map numeric status to string
                    status_value = sensor.get("status", 0)
                    if status_value == 2:
                        status = "critical"
                    elif status_value == 1:
                        status = "warning"
                    else:
                        status = "normal"

                    # Update sensor with string status for UI
                    sensor["status"] = status
                    tag_name = sensor.get("tag_name", "")

                    # Overall counts
                    if status == "normal":
                        normal += 1
                    elif status == "warning":
                        warning += 1
                    elif status == "critical":
                        critical += 1

                    # Station stats
                    station = tag_name.split("_")[0] if "_" in tag_name else "UNKNOWN"
                    if station not in station_stats:
                        station_stats[station] = {"normal": 0, "warning": 0, "critical": 0}
                    station_stats[station][status] = station_stats[station].get(status, 0) + 1

                    # System stats
                    parts = tag_name.split("_")
                    system = parts[1] if len(parts) > 1 else "UNKNOWN"
                    if system not in system_stats:
                        system_stats[system] = {"normal": 0, "warning": 0, "critical": 0}
                    system_stats[system][status] = system_stats[system].get(status, 0) + 1

            # Update state
            async with self:
                self.sensors = sensors_with_status
                self.normal_count = normal
                self.warning_count = warning
                self.critical_count = critical
                self.station_stats = station_stats
                self.system_stats = system_stats
                self.last_update = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%H:%M:%S")
                yield

        except Exception as e:
            console.error(f"Error fetching grouped data: {e}")
            async with self:
                self.last_update = f"Error: {str(e)[:50]}"
                yield

    def stop_streaming(self):
        """Stop streaming updates"""
        self.is_streaming = False
        console.info("Grouped dashboard streaming stopped")

    # =========================================================================
    # UI INTERACTION HANDLERS
    # =========================================================================

    def toggle_section(self, section_id: str):
        """Toggle expanded/collapsed state of a section"""
        if section_id in self.expanded_sections:
            self.expanded_sections.remove(section_id)
        else:
            self.expanded_sections.append(section_id)

    def is_section_expanded(self, section_id: str) -> bool:
        """Check if section is expanded"""
        return section_id in self.expanded_sections

    def expand_all_sections(self):
        """Expand all sections"""
        for station in self.grouped_sensors.keys():
            for system in self.grouped_sensors[station].keys():
                section_id = f"{station}_{system}"
                if section_id not in self.expanded_sections:
                    self.expanded_sections.append(section_id)

    def collapse_all_sections(self):
        """Collapse all sections"""
        self.expanded_sections = []

    def set_view_mode(self, mode: str):
        """Set view mode: grouped, flat, or compact"""
        self.view_mode = mode
        console.info(f"View mode changed to: {mode}")

    def toggle_critical_filter(self):
        """Toggle critical-only filter"""
        self.show_critical_only = not self.show_critical_only
        self.show_warnings_only = False  # Clear warning filter

    def toggle_warning_filter(self):
        """Toggle warning-only filter"""
        self.show_warnings_only = not self.show_warnings_only
        self.show_critical_only = False  # Clear critical filter

    def quick_filter_station(self, station: str):
        """Quick filter by station"""
        self.selected_station = station
        self.selected_system = "ALL"
        console.info(f"Quick filter: Station={station}")

    def quick_filter_system(self, system: str):
        """Quick filter by system"""
        self.selected_system = system
        console.info(f"Quick filter: System={system}")

    def reset_filters(self):
        """Reset all filters"""
        self.selected_station = "ALL"
        self.selected_system = "ALL"
        self.tag_search_query = ""
        self.show_critical_only = False
        self.show_warnings_only = False
        console.info("All filters reset")