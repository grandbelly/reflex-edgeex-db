"""Unified Dashboard Page - MVC + Real-time Pattern"""
from ..scada_config import scada_enabled
from ..states.scada_state import ScadaState
from ..views.scada_view import scada_view
import reflex as rx
from ..views.dashboard_realtime_view import dashboard_realtime_page
from ..states.dashboard_realtime import DashboardRealtimeState
from ..states.scheduler_state import SchedulerState
from ..components.layout import shell


@rx.page(
    route="/",
    title="Dashboard | edgeEX",
    on_load=ScadaState.initialize if scada_enabled() else [
        DashboardRealtimeState.start_streaming,
        SchedulerState.start_schedulers
    ]
)
def dashboard() -> rx.Component:
    """Main dashboard with real-time updates using MVC pattern"""
    if scada_enabled():
        return shell(scada_view("overview"), active_route="/")
    return shell(
        dashboard_realtime_page(),
        active_route="/"

    )