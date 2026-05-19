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

from .base import ModelPlugin

class ProphetPlugin(ModelPlugin):
    """Prophet model plugin"""

    def __init__(self, **params):
        super().__init__(**params)
        self.training_data = None

    def get_name(self) -> str:
        return "prophet"

    async def train(self, data: pd.DataFrame) -> Any:
        """Train Prophet model"""
        try:
            from prophet import Prophet

            # Prepare data
            df = data.copy()
            df['ds'] = df['timestamp']
            df['y'] = df['value']

            # Create and fit model
            model = Prophet(**self.params)
            model.fit(df[['ds', 'y']])

            # Store training data for evaluation
            self.training_data = df[['ds', 'y']].copy()
            
            self.model = model
            # 예측 구간 생성기 학습
            from ksys_app.ml.prediction_intervals import create_interval_generator

            try:
                self.interval_generator = create_interval_generator(
                    method=self.interval_method,
                    **self.interval_params
                )

                if self.interval_method == 'conformal':
                    # Conformal Prediction: 교차 검증으로 conformity scores 계산
                    self.interval_generator.fit(model, X.values, y)
                    console.info("✅ Conformal prediction intervals fitted")

                elif self.interval_method == 'bootstrap':
                    # Bootstrap: 학습 데이터 잔차 저장
                    y_pred = model.predict(X.values)
                    self.interval_generator.fit(y, y_pred)
                    console.info("✅ Bootstrap residuals collected")

                elif self.interval_method == 'quantile':
                    # Quantile Regression: 분위수별 모델 학습
                    import xgboost as xgb
                    self.interval_generator.fit(
                        xgb.XGBRegressor,
                        X.values,
                        y,
                        model_params=self.params
                    )
                    console.info("✅ Quantile regression models trained")

            except Exception as e:
                console.warn(f"Interval generator fitting failed: {e}")
                self.interval_generator = None

            console.info(f"✅ {self.get_name()} trained successfully")
            return self.model

        except ImportError:
            console.error("prophet not installed")
            raise
        except Exception as e:
            console.error(f"Error training Prophet: {e}")
            raise

    async def predict(self, horizon: int, level: list = None) -> pd.DataFrame:
        """Generate predictions with confidence intervals

        Args:
            horizon: Number of 10-minute periods to forecast
            level: List of confidence levels (ignored for Prophet, uses default 80%)
        """
        if self.model is None:
            raise ValueError("Model not trained")

        # Use 10-minute frequency to match training data (influx_agg_10m)
        future = self.model.make_future_dataframe(periods=horizon, freq='10T')
        forecast = self.model.predict(future)
        
        # Prophet uses yhat_lower/yhat_upper for 80% confidence by default
        result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(horizon).copy()
        
        # Rename to match expected format
        result = result.rename(columns={
            'yhat': 'Prophet',
            'yhat_lower': 'Prophet-lo-80',
            'yhat_upper': 'Prophet-hi-80'
        })
        
        # For 95% confidence, use wider interval (approximate)
        result['Prophet-lo-95'] = result['Prophet-lo-80'] * 1.2 - result['Prophet'] * 0.2
        result['Prophet-hi-95'] = result['Prophet-hi-80'] * 1.2 - result['Prophet'] * 0.2
        
        return result

    async def evaluate(self, test_data: pd.DataFrame = None, n_windows: int = 3, horizon: int = None) -> dict:
        """
        Evaluate Prophet model using simple train/test split

        Note: Prophet's cross_validation is unreliable with limited data,
        so we use a simple holdout validation approach instead.

        Args:
            test_data: Test dataset (optional, uses training data if not provided)
            n_windows: Number of walk-forward windows (ignored for simple split)
            horizon: Forecast horizon in periods (from forecast_config, used for validation split)

        Returns:
            dict with MAE, MAPE, MASE, RMSE, SMAPE, train_mae, validation_data
        """
        if self.model is None:
            raise ValueError("Model not trained")

        try:
            from prophet import Prophet

            # Use training data if test data not provided
            data = test_data if test_data is not None else self.training_data

            if data is None or len(data) == 0:
                console.log("No data available for Prophet evaluation")
                return {}

            # ✅ Convert column names if needed (timestamp→ds, value→y)
            data = data.copy()
            if 'timestamp' in data.columns and 'ds' not in data.columns:
                data['ds'] = data['timestamp']
            if 'value' in data.columns and 'y' not in data.columns:
                data['y'] = data['value']

            # Ensure we have required columns
            if 'ds' not in data.columns or 'y' not in data.columns:
                console.error(f"Prophet evaluate: missing required columns. Available: {data.columns.tolist()}")
                return {}

            # Calculate Train MAE using in-sample predictions
            train_mae = None
            try:
                # Use the already-trained model to predict on training data
                train_forecast = self.model.predict(self.training_data[['ds']])
                train_comparison = self.training_data[['ds', 'y']].merge(
                    train_forecast[['ds', 'yhat']],
                    on='ds',
                    how='inner'
                )
                if len(train_comparison) > 0:
                    train_actual = train_comparison['y'].values
                    train_pred = train_comparison['yhat'].values
                    train_mae = float(np.mean(np.abs(train_actual - train_pred)))
                    console.info(f"   Train MAE: {train_mae:.2f} (from {len(train_comparison)} training points)")
            except Exception as e:
                console.warn(f"Could not calculate train MAE: {e}")

            # ✅ Use SAME validation window as AutoARIMA for fair comparison
            # AutoARIMA uses last fold of walk-forward (same horizon size)
            # For consistency, use same validation window

            # horizon MUST be provided from forecast configuration
            if horizon is None:
                raise ValueError(
                    "Prophet evaluate() requires 'horizon' parameter from forecast configuration!\n"
                    "This should be passed from WalkForwardValidation.validate()"
                )

            # Use last 'horizon' points as test set (same as AutoARIMA's last fold)
            if len(data) < horizon + 10:  # Need at least 10 training points
                console.log(f"Insufficient data for validation (need >{horizon+10} points, have {len(data)})")
                return {}

            split_idx = len(data) - horizon

            # Split data - only use ds and y columns for Prophet
            train_df = data[['ds', 'y']].iloc[:split_idx].copy()
            test_df = data[['ds', 'y']].iloc[split_idx:].copy()

            console.log(f"Prophet validation: {len(train_df)} train, {len(test_df)} test points (horizon={horizon}, matched to AutoARIMA window)")

            # Create temporary Prophet model for validation
            val_model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=False,
                yearly_seasonality=False,
                interval_width=0.95
            )

            # Fit on train data
            val_model.fit(train_df)

            # Make predictions on test period
            future = test_df[['ds']].copy()
            forecast = val_model.predict(future)

            # Merge with actual values
            comparison = test_df[['ds', 'y']].merge(
                forecast[['ds', 'yhat']],
                on='ds',
                how='inner'
            )

            if len(comparison) == 0:
                console.log("No matching dates between actual and predicted")
                return {}

            # Calculate metrics
            y_true = comparison['y'].values
            y_pred = comparison['yhat'].values

            # MAE - Mean Absolute Error
            mae = float(np.mean(np.abs(y_true - y_pred)))

            # MAPE - Mean Absolute Percentage Error
            mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)

            # RMSE - Root Mean Squared Error
            rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

            # SMAPE - Symmetric Mean Absolute Percentage Error
            smape = float(np.mean(2.0 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred))) * 100)

            # MASE - Mean Absolute Scaled Error
            naive_error = np.mean(np.abs(np.diff(y_true)))
            mase = float(mae / naive_error) if naive_error > 0 else 0.0

            # Format validation data for chart display
            validation_data = [
                {
                    "ds": row['ds'].isoformat() if hasattr(row['ds'], 'isoformat') else str(row['ds']),
                    "actual": float(row['y']),
                    "predicted": float(row['yhat'])
                }
                for _, row in comparison.iterrows()
            ]

            train_mae_str = f"{train_mae:.2f}" if train_mae is not None else "N/A"
            console.log(f"Prophet metrics - Train MAE: {train_mae_str}")
            console.log(f"Prophet metrics - MAPE: {mape:.2f}%, MAE: {mae:.2f}, RMSE: {rmse:.2f}")
            console.log(f"Validation data: {len(validation_data)} points for chart")

            return {
                "train_mae": train_mae,  # Add train MAE
                "mae": mae,
                "mape": mape,
                "rmse": rmse,
                "smape": smape,
                "mase": mase,
                "validation_data": validation_data,
                "n_predictions": len(validation_data)
            }

        except Exception as e:
            console.error(f"Prophet evaluation error: {e}")
            import traceback
            traceback.print_exc()
            return {}


