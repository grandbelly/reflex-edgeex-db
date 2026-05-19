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

from ksys_app.services.feature_engineering_service import FeatureEngineeringService

KST = pytz.timezone('Asia/Seoul')


class FeatureEngineeringChain:
    """피처 엔지니어링 체인 빌더"""

    def __init__(self, pipeline: 'TrainingPipelineV2'):
        self.pipeline = pipeline
        self.config = {}

    def add_lag(self, periods: List[int]) -> 'FeatureEngineeringChain':
        self.config['lags'] = periods
        return self

    def add_rolling(self, windows: List[int]) -> 'FeatureEngineeringChain':
        self.config['rolling'] = windows
        return self

    def add_temporal(self, components: List[str]) -> 'FeatureEngineeringChain':
        self.config['temporal'] = components
        return self

    def add_fourier(self, periods: List[int]) -> 'FeatureEngineeringChain':
        self.config['fourier'] = periods
        return self

    def done(self) -> 'TrainingPipelineV2':
        """체인 완료 - 파이프라인으로 복귀"""
        self.pipeline._feature_config = self.config
        return self.pipeline


# ============================================================================
# Model Plugin (기존 설계 유지)
# ============================================================================
