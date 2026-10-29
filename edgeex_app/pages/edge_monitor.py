"""Edge Monitoring page (/edge-monitor) — real-time Kafka VQT, Alarms, and Health."""
from ..scada_config import scada_enabled
from ..states.scada_state import ScadaState
from ..views.scada_view import scada_view
import reflex as rx

from ..components.layout import shell
from ..states.edge_monitor_state import EdgeMonitorState
from ..views.edge_monitor_view import edge_monitor_view


@rx.page(
    route="/edge-monitor",
    title="Edge 관제 (Kafka) | edgeEX",
    on_load=ScadaState.initialize if scada_enabled() else EdgeMonitorState.initialize,
)
def edge_monitor_page() -> rx.Component:
    """EdgeEX Kafka VQT, Alarm, and Health monitoring page."""
    if scada_enabled():
        return shell(scada_view("flow"), active_route="/edge-monitor")
    return shell(
        edge_monitor_view(),
        active_route="/edge-monitor",
    )
