"""Reflex 0.10 SCADA entry point: native components and read-only routes."""
import reflex as rx
from .scada_config import scada_enabled

if not scada_enabled():
    raise RuntimeError("This application requires SCADA_DATA_SOURCE=edge_vqt")

# Legacy ORM models, write events and schedulers are not registered here.
from .pages import scada  # noqa: F401, E402

app = rx.App(
    style={"font_family": "'Segoe UI', 'Malgun Gothic', sans-serif",
           "font_variant_numeric": "tabular-nums"},
    stylesheets=["/scada.css"],
)
