"""Model plugins."""
from .base import ModelPlugin
from .autoarima import AutoARIMAPlugin
from .prophet import ProphetPlugin
from .xgboost import XGBoostPlugin

__all__ = ["ModelPlugin", "AutoARIMAPlugin", "ProphetPlugin", "XGBoostPlugin"]
