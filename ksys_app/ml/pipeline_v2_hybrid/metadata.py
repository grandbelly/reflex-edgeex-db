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


class PipelineMetadata:
    """파이프라인 실행 메타데이터"""

    # Data info
    tag_name: str = ""
    data_start: Optional[datetime] = None
    data_end: Optional[datetime] = None
    raw_samples: int = 0
    processed_samples: int = 0

    # Preprocessing steps
    preprocessing_steps: List[str] = field(default_factory=list)
    outliers_removed: int = 0
    interpolated_gaps: int = 0

    # Detailed preprocessing statistics
    preprocessing_details: Dict[str, Any] = field(default_factory=dict)
    # Example: {
    #   "outliers": {"removed": 10, "percentage": 1.5, "threshold": 3.0, "method": "z-score"},
    #   "interpolation": {"gaps_filled": 5, "method": "linear", "largest_gap": 3},
    # }

    # Feature engineering
    features_created: List[str] = field(default_factory=list)
    original_features: int = 0
    final_features: int = 0

    # Model training
    models_trained: List[str] = field(default_factory=list)
    training_duration: float = 0.0

    # Results
    best_model: str = ""
    best_mape: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'tag_name': self.tag_name,
            'data_start': self.data_start.isoformat() if self.data_start else None,
            'data_end': self.data_end.isoformat() if self.data_end else None,
            'raw_samples': self.raw_samples,
            'processed_samples': self.processed_samples,
            'preprocessing_steps': self.preprocessing_steps,
            'outliers_removed': self.outliers_removed,
            'features_created': self.features_created,
            'models_trained': self.models_trained,
            'best_model': self.best_model,
            'best_mape': self.best_mape
        }


# ============================================================================
# Preprocessing Chain (제안하신 설계의 PreprocessorChain)
# ============================================================================
