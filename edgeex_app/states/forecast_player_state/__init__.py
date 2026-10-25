"""forecast_player_state package — backward-compat re-export.

Existing import preserved:
    from edgeex_app.states.forecast_player_state import ForecastPlayerState  # noqa
"""
from .state import ForecastPlayerState

__all__ = ["ForecastPlayerState"]
