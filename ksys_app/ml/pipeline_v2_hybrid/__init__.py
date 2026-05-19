"""pipeline_v2_hybrid package — backward-compat re-exports.

Existing import paths preserved:
    from ksys_app.ml.pipeline_v2_hybrid import TrainingPipelineV2
    from ksys_app.ml.pipeline_v2_hybrid import AutoARIMAPlugin
    from ksys_app.ml.pipeline_v2_hybrid import create_pipeline_from_config
    ... etc.
"""
from .metadata import PipelineMetadata
from .preprocessing import (
    PreprocessingStep,
    InterpolateStep,
    RemoveOutliersStep,
    ScaleStep,
    PreprocessingChain,
)
from .features import FeatureEngineeringChain
from .plugins import (
    ModelPlugin,
    AutoARIMAPlugin,
    ProphetPlugin,
    XGBoostPlugin,
)
from .registry import ModelRegistry
from .training import TrainingPipelineV2, create_pipeline_from_config

__all__ = [
    "PipelineMetadata",
    "PreprocessingStep", "InterpolateStep", "RemoveOutliersStep", "ScaleStep", "PreprocessingChain",
    "FeatureEngineeringChain",
    "ModelPlugin", "AutoARIMAPlugin", "ProphetPlugin", "XGBoostPlugin",
    "ModelRegistry",
    "TrainingPipelineV2", "create_pipeline_from_config",
]
