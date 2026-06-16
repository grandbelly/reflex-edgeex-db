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

class XGBoostPlugin(ModelPlugin):
    """XGBoost model plugin with feature engineering and prediction intervals"""

    def __init__(
        self,
        interval_method: str = 'bootstrap',
        interval_params: dict = None,
        **params
    ):
        """
        Args:
            interval_method: 'conformal', 'bootstrap', 'quantile' 중 선택
            interval_params: 각 방법별 파라미터
            **params: XGBoost 모델 파라미터
        """
        super().__init__(**params)
        self.training_data = None
        self.last_timestamp = None

        # 예측 구간 생성 설정
        self.interval_method = interval_method
        self.interval_params = interval_params or {}
        self.interval_generator = None
        self.feature_cols = []

    def get_name(self) -> str:
        return "xgboost"

    async def train(self, data: pd.DataFrame) -> Any:
        """Train XGBoost model"""
        try:
            import xgboost as xgb

            # Prepare features (assume feature engineering already done)
            feature_cols = [c for c in data.columns if c not in ['timestamp', 'value', 'tag_name']]

            # If no features, create basic temporal features automatically
            if not feature_cols:
                console.warn("No features found - creating basic temporal features for XGBoost")
                data = data.copy()
                
                # Ensure timestamp is datetime and set as index
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                    data = data.set_index('timestamp')
                
                # Create temporal features from index
                data['hour'] = data.index.hour
                data['day_of_week'] = data.index.dayofweek
                data['is_weekend'] = (data.index.dayofweek >= 5).astype(int)
                
                # Add lag features
                data['lag_1'] = data['value'].shift(1)
                data['lag_24'] = data['value'].shift(24)
                data = data.dropna()  # Remove rows with NaN from lag features
                
                feature_cols = ['hour', 'day_of_week', 'is_weekend', 'lag_1', 'lag_24']
                console.info(f"Created {len(feature_cols)} basic features: {feature_cols}")

            X = data[feature_cols].fillna(0)
            y = data['value'].values

            # Default params
            params = {
                'objective': 'reg:squarederror',
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'random_state': 42,
                'n_jobs': -1
            }
            params.update(self.params)

            # Train
            model = xgb.XGBRegressor(**params)
            model.fit(X, y)

            self.model = model
            self.feature_cols = feature_cols
            
            # Store training data and last timestamp for prediction
            self.training_data = data.copy()
            self.last_timestamp = data.index[-1] if isinstance(data.index, pd.DatetimeIndex) else None
            
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
            console.error("xgboost not installed")
            raise
        except Exception as e:
            console.error(f"Error training XGBoost: {e}")
            raise

    async def predict(self, horizon: int, level: list = None) -> pd.DataFrame:
        """Generate predictions with future feature generation

        Args:
            horizon: Number of 10-minute periods to forecast
            level: List of confidence levels (ignored for XGBoost, uses bootstrapping)
        """
        if self.model is None:
            raise ValueError("Model not trained")

        try:
            # Generate future timestamps
            if self.last_timestamp is None:
                raise ValueError("No timestamp information available from training")

            # Use 10-minute frequency to match training data (influx_agg_10m)
            future_timestamps = pd.date_range(
                start=self.last_timestamp + pd.Timedelta(minutes=10),
                periods=horizon,
                freq='10T'
            )
            
            # Create empty DataFrame for future features
            future_df = pd.DataFrame(index=future_timestamps)
            
            # Generate temporal features
            future_df['hour'] = future_df.index.hour
            future_df['day_of_week'] = future_df.index.dayofweek
            future_df['is_weekend'] = (future_df.index.dayofweek >= 5).astype(int)
            
            # For lag features, use recursive prediction
            # Start with last known values from training
            last_values = self.training_data['value'].tail(24).values.tolist()
            predictions = []
            
            for i in range(horizon):
                # Create feature row
                feature_row = {
                    'hour': future_df.iloc[i]['hour'],
                    'day_of_week': future_df.iloc[i]['day_of_week'],
                    'is_weekend': future_df.iloc[i]['is_weekend'],
                    'lag_1': last_values[-1] if len(last_values) > 0 else 0,
                    'lag_24': last_values[-24] if len(last_values) >= 24 else last_values[0],
                }
                
                # Make prediction
                X_future = pd.DataFrame([feature_row])[self.feature_cols]
                pred = self.model.predict(X_future)[0]
                predictions.append(pred)
                
                # Update last_values for next iteration
                last_values.append(pred)
                if len(last_values) > 24:
                    last_values.pop(0)
            
            # Create result DataFrame
            result = pd.DataFrame({
                'ds': future_timestamps,
                'XGBoost': predictions,
            })
            
            # Generate prediction intervals using trained generator
            if self.interval_generator is not None:
                try:
                    predictions_array = np.array(predictions)

                    if self.interval_method == 'quantile':
                        # Quantile 방법은 X_future 필요
                        # Prepare X_future for all horizons
                        X_future_list = []
                        for i in range(horizon):
                            feature_row = {
                                'hour': future_df.iloc[i]['hour'],
                                'day_of_week': future_df.iloc[i]['day_of_week'],
                                'is_weekend': future_df.iloc[i]['is_weekend'],
                                'lag_1': 0,  # Simplified for interval generation
                                'lag_24': 0,
                            }
                            X_future_list.append(feature_row)
                        X_future = pd.DataFrame(X_future_list)[self.feature_cols]

                        intervals = self.interval_generator.generate(X_future=X_future.values)
                    else:
                        # Conformal, Bootstrap은 predictions만 필요
                        intervals = self.interval_generator.generate(predictions_array)

                    # Add intervals to result
                    for key, values in intervals.items():
                        result[f'XGBoost-{key}'] = values

                    console.info(f"Generated {self.interval_method} intervals: {list(intervals.keys())}")

                except Exception as e:
                    console.warn(f"Interval generation failed: {e}, using fallback")
                    # Fallback to simple intervals
                    result['XGBoost-lo-80'] = result['XGBoost'] * 0.9
                    result['XGBoost-hi-80'] = result['XGBoost'] * 1.1
                    result['XGBoost-lo-95'] = result['XGBoost'] * 0.8
                    result['XGBoost-hi-95'] = result['XGBoost'] * 1.2
            else:
                # No interval generator - use simple fallback
                result['XGBoost-lo-80'] = result['XGBoost'] * 0.9
                result['XGBoost-hi-80'] = result['XGBoost'] * 1.1
                result['XGBoost-lo-95'] = result['XGBoost'] * 0.8
                result['XGBoost-hi-95'] = result['XGBoost'] * 1.2
            
            console.info(f"Generated {len(result)} XGBoost predictions")
            return result

        except Exception as e:
            console.error(f"Error generating XGBoost predictions: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def evaluate(self, test_data: pd.DataFrame = None, n_windows: int = 3, horizon: int = None) -> dict:
        """
        Evaluate XGBoost model using walk-forward validation

        Args:
            test_data: Test dataset (optional, uses training data if not provided)
            n_windows: Number of walk-forward windows
            horizon: Forecast horizon in periods (from forecast_config, used for validation split)

        Returns:
            dict with MAE, MAPE, MASE, RMSE, SMAPE, train_mae, validation_data
        """
        if self.model is None:
            raise ValueError("Model not trained")

        try:
            # Use training data if test data not provided
            data = test_data if test_data is not None else self.training_data

            if data is None or len(data) == 0:
                console.log("No data available for XGBoost evaluation")
                return {}

            # ✅ Check if data has required feature columns, if not create them automatically
            missing_features = [col for col in self.feature_cols if col not in data.columns]
            if missing_features:
                console.warn(f"XGBoost evaluate: missing features {missing_features}, creating them automatically")

                # Create features automatically (same as train() method)
                data = data.copy()

                # Ensure timestamp is datetime and set as index
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                    data = data.set_index('timestamp')

                # Create temporal features from index
                data['hour'] = data.index.hour
                data['day_of_week'] = data.index.dayofweek
                data['is_weekend'] = (data.index.dayofweek >= 5).astype(int)

                # Add lag features
                data['lag_1'] = data['value'].shift(1)
                data['lag_24'] = data['value'].shift(24)
                data = data.dropna()  # Remove rows with NaN from lag features

                console.log(f"XGBoost evaluate: Created basic temporal features for validation")

            # Calculate Train MAE using training data predictions
            train_mae = None
            try:
                X_train = self.training_data[self.feature_cols].fillna(0)
                y_train_actual = self.training_data['value'].values
                y_train_pred = self.model.predict(X_train)
                train_mae = float(np.mean(np.abs(y_train_actual - y_train_pred)))
                console.info(f"   Train MAE: {train_mae:.2f} (from {len(y_train_actual)} training points)")
            except Exception as e:
                console.warn(f"Could not calculate train MAE: {e}")

            # ✅ Use SAME validation window as AutoARIMA for fair comparison
            # AutoARIMA uses last fold of walk-forward (same horizon size)
            # For consistency, use same validation window

            # horizon MUST be provided from forecast configuration
            if horizon is None:
                raise ValueError(
                    "XGBoost evaluate() requires 'horizon' parameter from forecast configuration!\n"
                    "This should be passed from WalkForwardValidation.validate()"
                )

            # Use last 'horizon' points as test set (same as AutoARIMA's last fold)
            if len(data) < horizon + 10:  # Need at least 10 training points
                console.log(f"Insufficient data for validation (need >{horizon+10} points, have {len(data)})")
                return {}

            split_idx = len(data) - horizon

            # Split data
            train_df = data.iloc[:split_idx].copy()
            test_df = data.iloc[split_idx:].copy()

            console.log(f"XGBoost validation: {len(train_df)} train, {len(test_df)} test points (horizon={horizon}, matched to AutoARIMA window)")

            # Get features
            X_test = test_df[self.feature_cols].fillna(0)
            y_true = test_df['value'].values

            # Make predictions
            y_pred = self.model.predict(X_test)

            # Calculate metrics
            mae = float(np.mean(np.abs(y_true - y_pred)))
            mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)
            rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
            smape = float(np.mean(2.0 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred))) * 100)

            # MASE
            naive_error = np.mean(np.abs(np.diff(y_true)))
            mase = float(mae / naive_error) if naive_error > 0 else 0.0

            # Format validation data for chart display
            validation_data = [
                {
                    "ds": test_df.index[i].isoformat() if hasattr(test_df.index[i], 'isoformat') else str(test_df.index[i]),
                    "actual": float(y_true[i]),
                    "predicted": float(y_pred[i])
                }
                for i in range(len(y_true))
            ]

            train_mae_str = f"{train_mae:.2f}" if train_mae is not None else "N/A"
            console.log(f"XGBoost metrics - Train MAE: {train_mae_str}")
            console.log(f"XGBoost metrics - MAPE: {mape:.2f}%, MAE: {mae:.2f}, RMSE: {rmse:.2f}")
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
            console.error(f"XGBoost evaluation error: {e}")
            import traceback
            traceback.print_exc()
            return {}


# ============================================================================
# Model Registry (제안하신 설계의 레지스트리 패턴)
# ============================================================================
