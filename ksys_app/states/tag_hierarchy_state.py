"""
Tag Hierarchy State
Manages Station/System/Tag hierarchical filtering
"""
import reflex as rx
from typing import List, Dict, Set
from ksys_app.states.base_state import BaseState
from ksys_app.db import q
from reflex.utils import console


class TagHierarchyState(BaseState):
    """State for managing tag hierarchy and filtering"""

    # All available tags from database
    all_tags: List[str] = []

    # Station/System structure
    tag_hierarchy: Dict[str, Dict[str, List[str]]] = {}
    # Example: {
    #   "S01": {
    #       "RAW": ["S01_RAW_FLOW_IN_PV", "S01_RAW_TEMP_PV"],
    #       "SR": ["S01_SR_PRESSURE_PV", ...],
    #   },
    #   "S02": {...}
    # }

    # Selection state
    selected_station: str = "ALL"
    selected_system: str = "ALL"
    selected_tags: List[str] = []

    # Search
    tag_search_query: str = ""

    # UI state
    is_hierarchy_loaded: bool = False

    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================

    @rx.var
    def available_stations(self) -> List[str]:
        """Get list of available stations"""
        stations = ["ALL"]
        if self.tag_hierarchy:
            stations.extend(sorted(self.tag_hierarchy.keys()))
        return stations

    @rx.var
    def available_systems(self) -> List[str]:
        """Get list of available systems based on selected station"""
        systems = ["ALL"]

        if self.selected_station == "ALL":
            # Get all unique systems from all stations
            all_systems = set()
            for station_data in self.tag_hierarchy.values():
                all_systems.update(station_data.keys())
            systems.extend(sorted(all_systems))
        elif self.selected_station in self.tag_hierarchy:
            # Get systems for selected station
            systems.extend(sorted(self.tag_hierarchy[self.selected_station].keys()))

        return systems

    @rx.var
    def filtered_tags(self) -> List[str]:
        """Get filtered tags based on station, system, and search query"""
        result = []

        # Start with all tags or filtered by station/system
        if self.selected_station == "ALL":
            # All tags
            if self.selected_system == "ALL":
                result = self.all_tags
            else:
                # Filter by system across all stations
                result = [
                    tag for tag in self.all_tags
                    if f"_{self.selected_system}_" in tag
                ]
        else:
            # Specific station
            if self.selected_station in self.tag_hierarchy:
                if self.selected_system == "ALL":
                    # All systems in station
                    station_tags = []
                    for system_tags in self.tag_hierarchy[self.selected_station].values():
                        station_tags.extend(system_tags)
                    result = station_tags
                else:
                    # Specific system in station
                    result = self.tag_hierarchy.get(self.selected_station, {}).get(
                        self.selected_system, []
                    )

        # Apply search filter
        if self.tag_search_query:
            query = self.tag_search_query.upper()
            result = [tag for tag in result if query in tag.upper()]

        return sorted(result)

    @rx.var
    def station_tag_counts(self) -> Dict[str, int]:
        """Get tag count per station"""
        counts = {}
        for station, systems in self.tag_hierarchy.items():
            total = sum(len(tags) for tags in systems.values())
            counts[station] = total
        return counts

    @rx.var
    def system_tag_counts(self) -> Dict[str, int]:
        """Get tag count per system in selected station"""
        if self.selected_station == "ALL":
            # Count across all stations
            counts = {}
            for station_data in self.tag_hierarchy.values():
                for system, tags in station_data.items():
                    counts[system] = counts.get(system, 0) + len(tags)
            return counts
        elif self.selected_station in self.tag_hierarchy:
            # Count for selected station
            return {
                system: len(tags)
                for system, tags in self.tag_hierarchy[self.selected_station].items()
            }
        return {}

    @rx.var
    def selected_tags_by_station(self) -> Dict[str, List[str]]:
        """Group selected tags by station"""
        grouped = {}
        for tag in self.selected_tags:
            station = tag.split("_")[0] if "_" in tag else "UNKNOWN"
            if station not in grouped:
                grouped[station] = []
            grouped[station].append(tag)
        return grouped

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    @rx.event(background=True)
    async def load_tag_hierarchy(self):
        """Load tag hierarchy from database"""
        console.info("Loading tag hierarchy...")

        try:
            # Get all tags with station and system info
            sql = """
                SELECT DISTINCT
                    tag_name,
                    SPLIT_PART(tag_name, '_', 1) as station,
                    SPLIT_PART(tag_name, '_', 2) as system
                FROM influx_tag
                WHERE tag_name IS NOT NULL
                  AND tag_name NOT LIKE 'TEST_%%'
                  AND tag_name NOT LIKE 'FEED_%%'
                  AND tag_name NOT LIKE 'PRODUCT_%%'
                  AND tag_name NOT LIKE 'RECOVERY_%%'
                  AND tag_name NOT LIKE 'INLET_%%'
                  AND tag_name NOT LIKE 'OUTLET_%%'
                  AND tag_name NOT LIKE 'PRESSURE_%%'
                  AND tag_name NOT LIKE 'OPERATING_%%'
                  AND tag_name NOT LIKE 'TOTAL_%%'
                ORDER BY tag_name
            """

            rows = await q(sql, ())

            # Build hierarchy
            hierarchy = {}
            all_tags = []

            for row in rows:
                tag_name = row["tag_name"]
                station = row["station"]
                system = row["system"]

                # Skip invalid entries
                if not station or not system:
                    continue

                all_tags.append(tag_name)

                # Build hierarchy
                if station not in hierarchy:
                    hierarchy[station] = {}
                if system not in hierarchy[station]:
                    hierarchy[station][system] = []
                hierarchy[station][system].append(tag_name)

            # Update state
            async with self:
                self.all_tags = all_tags
                self.tag_hierarchy = hierarchy
                self.is_hierarchy_loaded = True
                yield

            console.info(
                f"Loaded {len(all_tags)} tags: "
                f"{len(hierarchy)} stations, "
                f"{sum(len(systems) for systems in hierarchy.values())} systems"
            )

        except Exception as e:
            console.error(f"Error loading tag hierarchy: {e}")
            async with self:
                self.is_hierarchy_loaded = False
                yield

    def set_selected_station(self, station: str):
        """Set selected station and reset system selection"""
        self.selected_station = station
        self.selected_system = "ALL"
        console.info(f"Selected station: {station}")

    def set_selected_system(self, system: str):
        """Set selected system"""
        self.selected_system = system
        console.info(f"Selected system: {system}")

    def toggle_tag_selection(self, tag_name: str, checked: bool):
        """Toggle tag selection"""
        if checked and tag_name not in self.selected_tags:
            self.selected_tags.append(tag_name)
        elif not checked and tag_name in self.selected_tags:
            self.selected_tags.remove(tag_name)
        console.info(f"Selected tags: {len(self.selected_tags)}")

    def is_tag_selected(self, tag_name: str) -> bool:
        """Check if tag is selected"""
        return tag_name in self.selected_tags

    def clear_selected_tags(self):
        """Clear all selected tags"""
        self.selected_tags = []
        console.info("Cleared all selected tags")

    def select_top_tags(self):
        """Select top 5 tags from filtered list"""
        filtered = self.filtered_tags
        available = [tag for tag in filtered[:5] if tag not in self.selected_tags]
        self.selected_tags.extend(available)
        console.info(f"Selected top tags, total: {len(self.selected_tags)}")

    def remove_selected_tag(self, tag_name: str):
        """Remove a tag from selection"""
        if tag_name in self.selected_tags:
            self.selected_tags.remove(tag_name)
        console.info(f"Removed tag: {tag_name}")

    def select_all_in_system(self):
        """Select all tags in current system (up to limit)"""
        max_selections = 10  # Limit to prevent UI overload
        filtered = self.filtered_tags[:max_selections]
        for tag in filtered:
            if tag not in self.selected_tags:
                self.selected_tags.append(tag)
        console.info(f"Selected {len(filtered)} tags in system")

    def get_tag_station(self, tag_name: str) -> str:
        """Get station from tag name"""
        return tag_name.split("_")[0] if "_" in tag_name else "UNKNOWN"

    def get_tag_system(self, tag_name: str) -> str:
        """Get system from tag name"""
        parts = tag_name.split("_")
        return parts[1] if len(parts) > 1 else "UNKNOWN"