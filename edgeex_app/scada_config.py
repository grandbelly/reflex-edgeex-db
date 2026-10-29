"""Explicit, read-only migration profile for the six core SCADA routes."""
import os


def scada_enabled() -> bool:
    source = os.getenv("SCADA_DATA_SOURCE", "edge_vqt")
    if source not in {"legacy", "edge_vqt"}:
        raise ValueError("SCADA_DATA_SOURCE must be legacy or edge_vqt")
    return source == "edge_vqt"


def scada_server_settings() -> dict[str, str]:
    return {"default_transaction_read_only": "on"} if scada_enabled() else {}
