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

from .metadata import PipelineMetadata
from .preprocessing import PreprocessingChain
from .features import FeatureEngineeringChain
from .plugins import ModelPlugin, AutoARIMAPlugin, ProphetPlugin, XGBoostPlugin
from .registry import ModelRegistry

class TrainingPipelineV2:
    """
    하이브리드 학습 파이프라인

    Features:
    - 메서드 체이닝 (fluent API)
    - 전처리/후처리 체인
    - 메타데이터 추적
    - 레지스트리 패턴
    - 타입 안정성
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.feature_service = FeatureEngineeringService(session)

        # Configuration
        self._data_source = {}
        self._preprocessing_steps: List[PreprocessingStep] = []
        self._feature_config = {}
        self._models: List[ModelPlugin] = []
        self._validation = None

        # Data cache
        self._raw_data: Optional[pd.DataFrame] = None
        self._processed_data: Optional[pd.DataFrame] = None

        # Metadata
        self.metadata = PipelineMetadata()

    # ========================================================================
    # Fluent API
    # ========================================================================

    def set_data_source(self, tag_name: str, days: int = 30) -> 'TrainingPipelineV2':
        """데이터 소스 설정"""
        self._data_source = {'tag_name': tag_name, 'days': days}
        self.metadata.tag_name = tag_name
        return self

    def add_preprocessing(self) -> PreprocessingChain:
        """전처리 체인 시작"""
        return PreprocessingChain(self)

    def add_feature_engineering(self) -> FeatureEngineeringChain:
        """피처 엔지니어링 체인 시작"""
        return FeatureEngineeringChain(self)

    def add_model(self, model_type: str, **params) -> 'TrainingPipelineV2':
        """모델 추가 (레지스트리에서 가져오기)"""
        plugin_class = ModelRegistry.get(model_type)
        plugin = plugin_class(**params)
        self._models.append(plugin)
        console.info(f"➕ Added model: {plugin.get_name()}")
        return self

    def add_validation(self, validation_type: str, **params) -> 'TrainingPipelineV2':
        """검증 전략 추가"""
        from ksys_app.ml.pipeline_builder import WalkForwardValidation

        if validation_type == 'walk_forward':
            self._validation = WalkForwardValidation(**params)
        return self

    def build(self) -> 'TrainingPipelineV2':
        """파이프라인 빌드"""
        console.info("🔨 Pipeline V2 built successfully")
        console.info(f"   Preprocessing: {len(self._preprocessing_steps)} steps")
        console.info(f"   Features: {len(self._feature_config)} types")
        console.info(f"   Models: {len(self._models)}")
        return self

    # ========================================================================
    # Execution
    # ========================================================================

    async def execute(self) -> Dict[str, Any]:
        """파이프라인 실행"""
        import time
        start_time = time.time()

        console.info("🚀 Executing Pipeline V2...")

        # Step 1: Load data
        console.info("📥 Step 1: Loading data...")
        await self._load_data()

        # Step 2: Preprocessing
        if self._preprocessing_steps:
            console.info("🧹 Step 2: Preprocessing...")
            await self._apply_preprocessing()

        # Step 3: Feature engineering
        if self._feature_config:
            console.info("⚙️  Step 3: Feature engineering...")
            await self._apply_feature_engineering()

        # Step 4: Train models
        console.info("🎓 Step 4: Training models...")
        results = {}

        for model in self._models:
            console.info(f"   Training {model.get_name()}...")

            # Train
            await model.train(self._processed_data)
            self.metadata.models_trained.append(model.get_name())

            # Validate
            if self._validation:
                metrics = await self._validation.validate(self._processed_data, model)
                results[model.get_name()] = {
                    'model': model,
                    'metrics': metrics
                }
                console.info(f"   ✅ {model.get_name()} - MAPE: {metrics['mape']:.2f}%")

        # Find best model
        if results:
            best = min(results.items(), key=lambda x: x[1]['metrics'].get('mape', float('inf')))
            self.metadata.best_model = best[0]
            self.metadata.best_mape = best[1]['metrics']['mape']

        self.metadata.training_duration = time.time() - start_time

        console.info(f"✅ Pipeline complete in {self.metadata.training_duration:.2f}s")
        console.info(f"   Best model: {self.metadata.best_model} (MAPE: {self.metadata.best_mape:.2f}%)")

        return {
            'results': results,
            'metadata': self.metadata,
            'raw_data': self._raw_data  # Include raw data for chart display
        }

    # ========================================================================
    # Internal Methods
    # ========================================================================

    async def _load_data(self):
        """데이터 로드 - 10분 aggregation 데이터만 사용"""
        from sqlalchemy import text

        tag_name = self._data_source['tag_name']
        days = self._data_source['days']
        end_time = datetime.now(KST)
        start_time = end_time - timedelta(days=days)

        # ✅ 10분 aggregation 데이터만 사용 (성능 및 데이터 품질 향상)
        query = text("""
            SELECT
                bucket AT TIME ZONE 'Asia/Seoul' as timestamp,
                avg as value
            FROM (
                SELECT
                    time_bucket('10 minutes', ts) as bucket,
                    tag_name,
                    AVG(value) as avg
                FROM influx_hist
                WHERE quality = 0
                GROUP BY time_bucket('10 minutes', ts), tag_name
            ) agg_data
            WHERE tag_name = :tag_name
              AND bucket >= :start_time
              AND bucket < :end_time
              AND avg IS NOT NULL
            ORDER BY bucket
        """)

        rows = (await self.session.execute(
            query,
            {'tag_name': tag_name, 'start_time': start_time, 'end_time': end_time}
        )).mappings().all()

        self._raw_data = pd.DataFrame([dict(r) for r in rows])
        self.metadata.raw_samples = len(self._raw_data)
        self.metadata.data_start = start_time
        self.metadata.data_end = end_time

        console.info(f"   Loaded {len(self._raw_data)} rows")

    async def _apply_preprocessing(self):
        """전처리 체인 실행"""
        df = self._raw_data.copy()

        for step in self._preprocessing_steps:
            df = await step.apply(df, self.metadata)

        self._processed_data = df
        self.metadata.processed_samples = len(df)
        console.info(f"   Processed samples: {self.metadata.processed_samples}")

    async def _apply_feature_engineering(self):
        """피처 엔지니어링 적용"""
        df = self._processed_data if self._processed_data is not None else self._raw_data
        df = df.copy()

        self.metadata.original_features = len(df.columns)

        # Lag features
        if self._feature_config.get('lags'):
            for lag in self._feature_config['lags']:
                df[f'lag_{lag}h'] = df['value'].shift(lag)
                self.metadata.features_created.append(f'lag_{lag}h')

        # Rolling features
        if self._feature_config.get('rolling'):
            for window in self._feature_config['rolling']:
                df[f'rolling_mean_{window}h'] = df['value'].rolling(window).mean()
                df[f'rolling_std_{window}h'] = df['value'].rolling(window).std()
                self.metadata.features_created.extend([
                    f'rolling_mean_{window}h',
                    f'rolling_std_{window}h'
                ])

        # Temporal features
        if self._feature_config.get('temporal'):
            for comp in self._feature_config['temporal']:
                if comp == 'hour':
                    df['hour'] = df['timestamp'].dt.hour
                    self.metadata.features_created.append('hour')
                elif comp == 'dayofweek':
                    df['dayofweek'] = df['timestamp'].dt.dayofweek
                    self.metadata.features_created.append('dayofweek')

        df = df.dropna()
        self._processed_data = df
        self.metadata.final_features = len(df.columns)

        console.info(f"   Created {len(self.metadata.features_created)} features")


# ============================================================================
# Configuration-based Factory (제안하신 설계)
# ============================================================================

async def create_pipeline_from_config(
    session: AsyncSession,
    config: Dict
) -> TrainingPipelineV2:
    """설정 기반 파이프라인 생성"""

    pipeline = TrainingPipelineV2(session)

    # Data source
    if 'data_source' in config:
        pipeline.set_data_source(**config['data_source'])

    # Preprocessing
    if 'preprocessing' in config:
        chain = pipeline.add_preprocessing()
        for step in config['preprocessing']:
            if step['type'] == 'interpolate':
                chain.interpolate(**step.get('params', {}))
            elif step['type'] == 'remove_outliers':
                chain.remove_outliers(**step.get('params', {}))
            elif step['type'] == 'scale':
                chain.scale(**step.get('params', {}))
        chain.done()

    # Feature engineering
    if 'feature_engineering' in config:
        chain = pipeline.add_feature_engineering()
        fe_config = config['feature_engineering']

        if 'lags' in fe_config:
            chain.add_lag(fe_config['lags'])
        if 'rolling' in fe_config:
            chain.add_rolling(fe_config['rolling'])
        if 'temporal' in fe_config:
            chain.add_temporal(fe_config['temporal'])

        chain.done()

    # Models
    if 'models' in config:
        for model_cfg in config['models']:
            pipeline.add_model(model_cfg['type'], **model_cfg.get('params', {}))

    # Validation
    if 'validation' in config:
        pipeline.add_validation(
            config['validation']['type'],
            **config['validation'].get('params', {})
        )

    return pipeline.build()