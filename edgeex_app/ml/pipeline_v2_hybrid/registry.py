"""Auto-split from pipeline_v2_hybrid.py — see ml/pipeline_v2_hybrid/__init__.py for index."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
import pytz

from reflex.utils import console
from sqlalchemy.ext.asyncio import AsyncSession

from edgeex_app.services.feature_engineering_service import FeatureEngineeringService

KST = pytz.timezone('Asia/Seoul')


class ModelRegistry:
    """모델 레지스트리 - 동적 알고리즘 추가"""

    _models: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, plugin_class: type):
        """새로운 모델 등록"""
        if not issubclass(plugin_class, ModelPlugin):
            raise TypeError("Must inherit from ModelPlugin")

        cls._models[name] = plugin_class
        console.info(f"📦 Registered model: {name}")

    @classmethod
    def get(cls, name: str) -> type:
        """모델 클래스 가져오기"""
        if name not in cls._models:
            raise ValueError(f"Model '{name}' not registered")
        return cls._models[name]

    @classmethod
    def list_models(cls) -> List[str]:
        """등록된 모델 목록"""
        return list(cls._models.keys())


# Default models registration
ModelRegistry.register('auto_arima', AutoARIMAPlugin)
ModelRegistry.register('prophet', ProphetPlugin)
ModelRegistry.register('xgboost', XGBoostPlugin)


# ============================================================================
# Hybrid Training Pipeline V2
# ============================================================================
