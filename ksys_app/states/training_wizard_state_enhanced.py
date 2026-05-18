"""
Training Wizard State Enhanced - With Hierarchical Tag Selection
Extends TrainingWizardState with TagHierarchyState for Station/System filtering
"""

import reflex as rx
from reflex.utils import console
from typing import List, Dict, Any

from .training_wizard_state import TrainingWizardState
from .tag_hierarchy_state import TagHierarchyState
from ..db_orm import get_async_session


class TrainingWizardStateEnhanced(TrainingWizardState, TagHierarchyState):
    """Training Wizard State with Hierarchical Tag Selection"""

    # Search filter for tags
    tag_search_query: str = ""

    # =========================================================================
    # Computed Properties for Hierarchical Tag Selection
    # =========================================================================

    @rx.var(cache=True)
    def filtered_available_tags(self) -> List[str]:
        """
        Filter available_tags based on Station/System selection and search query.
        Uses the tag hierarchy from TagHierarchyState.
        """
        if not self.available_tags:
            return []

        result = self.available_tags

        # Filter by Station
        if self.selected_station != "ALL":
            result = [
                tag for tag in result
                if tag.startswith(f"{self.selected_station}_")
            ]

        # Filter by System
        if self.selected_system != "ALL":
            result = [
                tag for tag in result
                if self._tag_matches_system(tag, self.selected_system)
            ]

        # Filter by search query
        if self.tag_search_query:
            query = self.tag_search_query.lower()
            result = [
                tag for tag in result
                if query in tag.lower()
            ]

        return sorted(result)

    def _tag_matches_system(self, tag: str, system: str) -> bool:
        """Check if tag belongs to the specified system"""
        parts = tag.split('_')
        if len(parts) >= 2:
            return parts[1] == system
        return False

    @rx.var
    def tag_count_by_station(self) -> Dict[str, int]:
        """Count available tags by station"""
        counts = {"S01": 0, "S02": 0, "OTHER": 0}
        for tag in self.available_tags:
            if tag.startswith("S01_"):
                counts["S01"] += 1
            elif tag.startswith("S02_"):
                counts["S02"] += 1
            else:
                counts["OTHER"] += 1
        return counts

    @rx.var
    def systems_for_station(self) -> List[str]:
        """Get list of systems available for the selected station"""
        systems = set()
        for tag in self.available_tags:
            parts = tag.split('_')
            if len(parts) >= 2:
                station = parts[0]
                system = parts[1]
                # Filter by selected station
                if self.selected_station == "ALL" or station == self.selected_station:
                    systems.add(system)
        return ["ALL"] + sorted(list(systems))

    @rx.var
    def filtered_tags_count(self) -> int:
        """Number of tags after filtering"""
        return len(self.filtered_available_tags)

    @rx.var
    def selected_tag_info(self) -> Dict[str, str]:
        """Parse selected tag into station/system/name components"""
        if not self.selected_tag:
            return {"station": "", "system": "", "name": ""}

        parts = self.selected_tag.split('_')
        if len(parts) >= 3:
            return {
                "station": parts[0],
                "system": parts[1],
                "name": '_'.join(parts[2:])
            }
        return {"station": "", "system": "", "name": self.selected_tag}

    # =========================================================================
    # Event Handlers
    # =========================================================================

    @rx.event
    def set_tag_search_query(self, query: str):
        """Update tag search query"""
        self.tag_search_query = query

    @rx.event
    def clear_tag_search(self):
        """Clear tag search query"""
        self.tag_search_query = ""

    @rx.event
    def select_tag_from_hierarchy(self, tag: str):
        """Select a tag from the hierarchical selector"""
        self.selected_tag = tag
        console.log(f"[TrainingWizardEnhanced] Selected tag: {tag}")

    @rx.event
    def set_selected_station(self, station: str):
        """Override to also reset system and tag when station changes"""
        self.selected_station = station
        self.selected_system = "ALL"
        # Don't clear selected_tag here - let user keep their selection
        self.tag_search_query = ""
        console.log(f"[TrainingWizardEnhanced] Station changed to: {station}")

    @rx.event
    def set_selected_system(self, system: str):
        """Override to reset search when system changes"""
        self.selected_system = system
        self.tag_search_query = ""
        console.log(f"[TrainingWizardEnhanced] System changed to: {system}")

    @rx.event(background=True)
    async def initialize_wizard_enhanced(self):
        """Initialize wizard with tag hierarchy"""
        console.log("=== TrainingWizardStateEnhanced.initialize_wizard_enhanced() STARTED ===")

        # First load tag hierarchy
        if not self.is_hierarchy_loaded:
            yield TrainingWizardStateEnhanced.load_tag_hierarchy

        # Then call parent initialization
        yield TrainingWizardStateEnhanced.initialize_wizard()

        console.log("=== TrainingWizardStateEnhanced.initialize_wizard_enhanced() COMPLETE ===")
