"""dashboard package — backward-compat re-export.

Existing import preserved:
    from ksys_app.states.dashboard import DashboardState  # noqa
"""
from .state import DashboardState
from . import utils  # expose utils submodule

__all__ = ["DashboardState", "utils"]
