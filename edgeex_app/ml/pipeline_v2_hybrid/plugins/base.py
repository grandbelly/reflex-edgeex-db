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


class ModelPlugin(ABC):
    """모델 플러그인 베이스 클래스"""

    def __init__(self, **params):
        self.params = params
        self.model = None

    @abstractmethod
    async def train(self, data: pd.DataFrame) -> Any:
        pass

    @abstractmethod
    async def predict(self, horizon: int) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

