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


class PreprocessingStep(ABC):
    """전처리 단계 베이스 클래스"""

    @abstractmethod
    async def apply(self, df: pd.DataFrame, metadata: PipelineMetadata) -> pd.DataFrame:
        """전처리 적용"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """단계 이름"""
        pass


class InterpolateStep(PreprocessingStep):
    """결측치 보간"""

    def __init__(self, method: str = 'linear'):
        self.method = method

    async def apply(self, df: pd.DataFrame, metadata: PipelineMetadata) -> pd.DataFrame:
        before_count = df['value'].isna().sum()

        # Find gap sizes before interpolation
        gaps = df['value'].isna()
        gap_sizes = []
        current_gap = 0
        for is_gap in gaps:
            if is_gap:
                current_gap += 1
            else:
                if current_gap > 0:
                    gap_sizes.append(current_gap)
                current_gap = 0
        if current_gap > 0:
            gap_sizes.append(current_gap)

        # Perform interpolation
        df['value'] = df['value'].interpolate(method=self.method)
        after_count = df['value'].isna().sum()

        filled_count = before_count - after_count
        metadata.interpolated_gaps = filled_count
        metadata.preprocessing_steps.append(f"interpolate_{self.method}")

        # Store detailed statistics
        metadata.preprocessing_details['interpolation'] = {
            "gaps_filled": filled_count,
            "method": self.method,
            "total_gaps": len(gap_sizes),
            "largest_gap": max(gap_sizes) if gap_sizes else 0,
            "average_gap_size": sum(gap_sizes) / len(gap_sizes) if gap_sizes else 0,
            "percentage": (filled_count / len(df) * 100) if len(df) > 0 else 0,
        }

        console.info(f"   ✓ Interpolated {filled_count} gaps using {self.method} (largest: {metadata.preprocessing_details['interpolation']['largest_gap']})")
        return df

    def get_name(self) -> str:
        return f"interpolate_{self.method}"


class RemoveOutliersStep(PreprocessingStep):
    """이상치 제거 (Z-score 기반)"""

    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold

    async def apply(self, df: pd.DataFrame, metadata: PipelineMetadata) -> pd.DataFrame:
        # Calculate statistics before outlier removal
        mean_before = df['value'].mean()
        std_before = df['value'].std()

        z_scores = np.abs((df['value'] - mean_before) / std_before)
        before = len(df)
        df = df[z_scores < self.threshold].copy()
        after = len(df)

        removed_count = before - after
        metadata.outliers_removed = removed_count
        metadata.preprocessing_steps.append(f"remove_outliers_{self.threshold}")

        # Store detailed statistics
        metadata.preprocessing_details['outliers'] = {
            "removed": removed_count,
            "percentage": (removed_count / before * 100) if before > 0 else 0,
            "threshold": self.threshold,
            "method": "z-score",
            "mean_before": float(mean_before),
            "std_before": float(std_before),
            "mean_after": float(df['value'].mean()),
            "std_after": float(df['value'].std()),
        }

        console.info(f"   ✓ Removed {removed_count} outliers ({metadata.preprocessing_details['outliers']['percentage']:.2f}%)")
        return df

    def get_name(self) -> str:
        return f"remove_outliers_{self.threshold}"


class ScaleStep(PreprocessingStep):
    """스케일링"""

    def __init__(self, method: str = 'standard'):
        self.method = method

    async def apply(self, df: pd.DataFrame, metadata: PipelineMetadata) -> pd.DataFrame:
        if self.method == 'standard':
            df['value_scaled'] = (df['value'] - df['value'].mean()) / df['value'].std()
        elif self.method == 'minmax':
            df['value_scaled'] = (df['value'] - df['value'].min()) / (df['value'].max() - df['value'].min())

        metadata.preprocessing_steps.append(f"scale_{self.method}")
        console.info(f"   ✓ Scaled with {self.method}")
        return df

    def get_name(self) -> str:
        return f"scale_{self.method}"


class PreprocessingChain:
    """전처리 체인 빌더"""

    def __init__(self, pipeline: 'TrainingPipelineV2'):
        self.pipeline = pipeline
        self.steps: List[PreprocessingStep] = []

    def interpolate(self, method: str = 'linear') -> 'PreprocessingChain':
        self.steps.append(InterpolateStep(method))
        return self

    def remove_outliers(self, threshold: float = 3.0) -> 'PreprocessingChain':
        self.steps.append(RemoveOutliersStep(threshold))
        return self

    def scale(self, method: str = 'standard') -> 'PreprocessingChain':
        self.steps.append(ScaleStep(method))
        return self

    def done(self) -> 'TrainingPipelineV2':
        """체인 완료 - 파이프라인으로 복귀"""
        self.pipeline._preprocessing_steps = self.steps
        return self.pipeline


# ============================================================================
# Feature Engineering Chain
# ============================================================================
