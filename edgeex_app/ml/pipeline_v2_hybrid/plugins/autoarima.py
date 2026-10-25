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

from .base import ModelPlugin

class AutoARIMAPlugin(ModelPlugin):
    """Auto ARIMA model plugin using statsforecast with diagnostics"""

    def __init__(self, **params):
        super().__init__(**params)
        self.training_data = None
        self.model_info = {}  # Store ARIMA parameters, residuals, etc.

    def get_name(self) -> str:
        return "auto_arima"

    async def train(self, data: pd.DataFrame) -> Any:
        """Train Auto ARIMA model with full diagnostics"""
        try:
            from statsforecast import StatsForecast
            from statsforecast.models import AutoARIMA
            from statsforecast.arima import arima_string

            # Prepare data for statsforecast
            df = data.copy()
            df['ds'] = df['timestamp']
            df['y'] = df['value']
            df['unique_id'] = 'series_1'

            # Store training data for later use
            self.training_data = df[['unique_id', 'ds', 'y']].copy()

            # Create model with season_length based on data frequency
            # Data is 10-minute intervals: 6 per hour * 24 hours = 144 for daily seasonality
            season_length = self.params.get('season_length', 144)  # Default: 10-min data with daily seasonality
            models = [AutoARIMA(season_length=season_length)]
            sf = StatsForecast(models=models, freq='10T', n_jobs=1)  # 10T = 10 minute frequency

            # Fit model
            console.info(f"Training {self.get_name()} with season_length={season_length}...")
            sf.fit(self.training_data)

            self.model = sf

            # Extract model diagnostics
            try:
                fitted_model = sf.fitted_[0, 0].model_

                # Get ARIMA string representation (e.g., "ARIMA(4,0,3)(0,1,1)[12]")
                arima_params = arima_string(fitted_model)
                self.model_info['arima_string'] = arima_params.strip()

                # Get model parameters
                self.model_info['arma'] = fitted_model.get('arma', None)
                self.model_info['aic'] = fitted_model.get('aic', None)
                self.model_info['bic'] = fitted_model.get('bic', None)
                self.model_info['aicc'] = fitted_model.get('aicc', None)
                self.model_info['sigma2'] = fitted_model.get('sigma2', None)

                # Get residuals for diagnostic plots
                residuals = fitted_model.get('residuals', None)
                if residuals is not None:
                    self.model_info['residuals'] = residuals
                    self.model_info['residuals_mean'] = float(np.mean(residuals))
                    self.model_info['residuals_std'] = float(np.std(residuals))

                console.info(f"✅ {self.get_name()} trained: {self.model_info['arima_string']}")
                console.info(f"   AIC: {self.model_info['aic']:.2f}, BIC: {self.model_info['bic']:.2f}")

            except Exception as e:
                console.warn(f"Could not extract model diagnostics: {e}")

            return self.model

        except ImportError:
            console.error("statsforecast not installed")
            raise
        except Exception as e:
            console.error(f"Error training AutoARIMA: {e}")
            raise

    async def predict(self, horizon: int, level: list = None) -> pd.DataFrame:
        """
        Generate predictions with confidence intervals

        Args:
            horizon: Number of periods to forecast
            level: List of confidence levels (e.g., [80, 95])
        """
        if self.model is None:
            raise ValueError("Model not trained")

        # Generate forecast with confidence intervals
        if level:
            forecast = self.model.predict(h=horizon, level=level)
            console.info(f"Forecast generated with {len(level)} confidence intervals")
        else:
            forecast = self.model.predict(h=horizon)

        return forecast

    def get_fitted_values(self) -> pd.DataFrame:
        """Get fitted values from training"""
        if self.model is None:
            raise ValueError("Model not trained")

        try:
            # statsforecast stores fitted values in fitted_ attribute
            # fitted_ is a DataFrame with columns: unique_id, ds, AutoARIMA (fitted values)
            if hasattr(self.model, 'fitted_'):
                fitted_df = self.model.fitted_
                console.debug(f"Found fitted values: {fitted_df.shape if fitted_df is not None else 'None'}")
                return fitted_df
            else:
                console.warn("Model has no fitted_ attribute")
                return None
        except Exception as e:
            console.warn(f"Could not get fitted values: {e}")
            return None

    async def evaluate(self, test_data: pd.DataFrame = None, n_windows: int = 3, horizon: int = None) -> dict:
        """
        Evaluate model performance with walk-forward validation

        Args:
            test_data: Test dataset (optional, uses training data if not provided)
            n_windows: Number of walk-forward windows
            horizon: Forecast horizon in periods (from forecast_config, e.g., 36 for 6h @ 10-min intervals)

        Returns:
            dict with MAE, MAPE, MASE, RMSE, SMAPE, train_mae
        """
        if self.model is None:
            raise ValueError("Model not trained")

        try:
            # Use training data if test data not provided
            data = test_data if test_data is not None else self.training_data

            if data is None or len(data) == 0:
                console.log("No data available for Auto-ARIMA evaluation")
                return {}

            # ✅ Convert column names if needed (timestamp→ds, value→y)
            data = data.copy()
            if 'timestamp' in data.columns and 'ds' not in data.columns:
                data['ds'] = data['timestamp']
            if 'value' in data.columns and 'y' not in data.columns:
                data['y'] = data['value']

            # Ensure required columns and unique_id
            if 'unique_id' not in data.columns:
                data['unique_id'] = 'series_1'

            # Ensure we have required columns
            if 'ds' not in data.columns or 'y' not in data.columns:
                console.error(f"Auto-ARIMA evaluate: missing required columns. Available: {data.columns.tolist()}")
                return {}

            # NOTE: statsforecast AutoARIMA does not provide fitted values
            # predict(h=n) forecasts FUTURE values, not in-sample fitted values
            # Therefore, train_mae cannot be accurately calculated for AutoARIMA
            # Unlike Prophet/XGBoost which support in-sample predictions
            train_mae = None
            console.info("   ⚠️ Train MAE not calculated for AutoARIMA (statsforecast limitation)")

            # Perform cross-validation with walk-forward
            # ✅ Use user-configured horizon (e.g., 36 for 6h @ 10-min) instead of hardcoded 24
            if horizon is None:
                # Fallback to old behavior (for backward compatibility)
                horizon = min(24, len(data) // (n_windows + 1))
                console.warn(f"⚠️ No horizon provided, using fallback: {horizon}")

            # ✅ FIX: Validate that we have enough data for walk-forward validation
            # Required data: (n_windows * step_size) + horizon
            # Use horizon as step_size for non-overlapping windows
            required_data_points = (n_windows * horizon) + horizon
            if len(data) < required_data_points:
                console.warn(f"⚠️ Insufficient data for walk-forward validation")
                console.warn(f"   Required: {required_data_points} points ({n_windows} windows × {horizon} step + {horizon} test)")
                console.warn(f"   Available: {len(data)} points")
                # Reduce n_windows to fit available data
                max_windows = max(1, (len(data) - horizon) // horizon)
                if max_windows < n_windows:
                    n_windows = max_windows
                    console.warn(f"   Reducing to {n_windows} windows to fit available data")
                if n_windows < 1:
                    console.error("Not enough data for even 1 validation window")
                    return {}

            console.info(f"Evaluating with {n_windows} windows, horizon={horizon}, step_size={horizon}")

            cv_results = self.model.cross_validation(
                df=data[['unique_id', 'ds', 'y']],  # Only required columns
                h=horizon,
                step_size=horizon,  # Use same as horizon for non-overlapping windows
                n_windows=n_windows
            )

            # 🔍 DEBUG: Check cv_results
            console.debug(f"cv_results shape: {cv_results.shape if cv_results is not None else 'None'}")
            console.debug(f"cv_results columns: {cv_results.columns.tolist() if cv_results is not None else 'None'}")
            if cv_results is not None and len(cv_results) > 0:
                console.debug(f"cv_results first 3 rows:\n{cv_results.head(3)}")
                console.debug(f"cv_results unique cutoffs: {cv_results['cutoff'].unique() if 'cutoff' in cv_results.columns else 'No cutoff'}")

            # Calculate metrics
            actual = cv_results['y'].values
            predicted = cv_results['AutoARIMA'].values

            console.debug(f"actual shape: {actual.shape}, predicted shape: {predicted.shape}")
            console.debug(f"actual sample: {actual[:5]}")
            console.debug(f"predicted sample: {predicted[:5]}")

            # MAE - Mean Absolute Error
            mae = float(np.mean(np.abs(actual - predicted)))

            # MAPE - Mean Absolute Percentage Error
            mape = float(np.mean(np.abs((actual - predicted) / actual)) * 100)

            # RMSE - Root Mean Squared Error
            rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))

            # SMAPE - Symmetric Mean Absolute Percentage Error
            smape = float(np.mean(2 * np.abs(actual - predicted) / (np.abs(actual) + np.abs(predicted))) * 100)

            # MASE - Mean Absolute Scaled Error (using naive forecast as baseline)
            naive_error = np.mean(np.abs(np.diff(actual)))
            mase = float(mae / naive_error) if naive_error > 0 else 0.0

            # Extract actual vs predicted data for visualization
            validation_data = []
            for idx, row in cv_results.iterrows():
                validation_data.append({
                    "ds": row['ds'].isoformat() if hasattr(row['ds'], 'isoformat') else str(row['ds']),
                    "actual": float(row['y']),
                    "predicted": float(row['AutoARIMA']),
                })

            # ✅ NEW: Extract fold-by-fold results for detailed analysis
            fold_results = []
            if 'cutoff' in cv_results.columns:
                # Group by cutoff (each cutoff represents one fold)
                for fold_num, (cutoff_date, fold_data) in enumerate(cv_results.groupby('cutoff'), start=1):
                    fold_actual = fold_data['y'].values
                    fold_pred = fold_data['AutoARIMA'].values

                    # Calculate metrics for this fold
                    fold_mae = float(np.mean(np.abs(fold_actual - fold_pred)))
                    fold_mape = float(np.mean(np.abs((fold_actual - fold_pred) / fold_actual)) * 100)
                    fold_rmse = float(np.sqrt(np.mean((fold_actual - fold_pred) ** 2)))

                    # Extract fold validation data
                    fold_validation_data = [
                        {
                            "ds": row['ds'].isoformat() if hasattr(row['ds'], 'isoformat') else str(row['ds']),
                            "actual": float(row['y']),
                            "predicted": float(row['AutoARIMA']),
                        }
                        for _, row in fold_data.iterrows()
                    ]

                    # Format values for display (2 decimal places for metrics, date-only for cutoff)
                    cutoff_str = cutoff_date.isoformat() if hasattr(cutoff_date, 'isoformat') else str(cutoff_date)
                    if 'T' in cutoff_str:
                        cutoff_str = cutoff_str.split('T')[0]  # Extract date part only

                    fold_results.append({
                        "fold": fold_num,
                        "cutoff": cutoff_str,
                        "n_points": len(fold_data),
                        "mae": round(fold_mae, 2),
                        "mape": round(fold_mape, 2),
                        "rmse": round(fold_rmse, 2),
                        "validation_data": fold_validation_data
                    })

                console.info(f"   Extracted {len(fold_results)} fold results for detailed analysis")

            metrics = {
                "train_mae": train_mae,  # Add train MAE
                "mae": mae,
                "mape": mape,
                "mase": mase,
                "rmse": rmse,
                "smape": smape,
                "n_windows": n_windows,
                "horizon": horizon,
                "n_predictions": len(actual),
                "validation_data": validation_data,  # Add actual vs predicted pairs
                "fold_results": fold_results,  # ✅ NEW: Fold-by-fold results for detailed view
            }

            train_mae_str = f"{train_mae:.2f}" if train_mae is not None else "N/A"
            console.info(f"   Train MAE: {train_mae_str}")
            console.info(f"   Val MAE: {mae:.2f}, MAPE: {mape:.2f}%, RMSE: {rmse:.2f}")
            console.info(f"   Validation data: {len(validation_data)} points for chart")

            return metrics

        except Exception as e:
            console.warn(f"Could not evaluate model: {e}")
            return {}

    def get_residuals_analysis(self) -> dict:
        """
        Analyze residuals for diagnostic purposes
        
        Returns:
            dict with residuals statistics and histogram data
        """
        if self.model is None or 'residuals' not in self.model_info:
            return {}
        
        try:
            residuals = self.model_info['residuals']
            
            # Basic statistics
            residuals_mean = float(np.mean(residuals))
            residuals_std = float(np.std(residuals))
            residuals_min = float(np.min(residuals))
            residuals_max = float(np.max(residuals))
            
            # Normality tests
            from scipy import stats
            skewness = float(stats.skew(residuals))
            kurtosis = float(stats.kurtosis(residuals))
            
            # Q-Q plot data (quantiles)
            theoretical_quantiles = stats.norm.ppf(np.linspace(0.01, 0.99, 50))
            sample_quantiles = np.percentile(residuals, np.linspace(1, 99, 50))
            
            # Histogram data (bins)
            hist_counts, hist_edges = np.histogram(residuals, bins=20)
            histogram_data = [
                {
                    "bin_start": float(hist_edges[i]),
                    "bin_end": float(hist_edges[i+1]),
                    "count": int(hist_counts[i]),
                    "bin_center": float((hist_edges[i] + hist_edges[i+1]) / 2)
                }
                for i in range(len(hist_counts))
            ]
            
            # ACF data (autocorrelation function)
            from statsmodels.tsa.stattools import acf
            acf_values = acf(residuals, nlags=24, fft=False)
            acf_data = [
                {"lag": i, "acf": float(acf_values[i])}
                for i in range(len(acf_values))
            ]
            
            analysis = {
                "statistics": {
                    "mean": residuals_mean,
                    "std": residuals_std,
                    "min": residuals_min,
                    "max": residuals_max,
                    "skewness": skewness,
                    "kurtosis": kurtosis,
                },
                "qq_plot": {
                    "theoretical": theoretical_quantiles.tolist(),
                    "sample": sample_quantiles.tolist(),
                },
                "histogram": histogram_data,
                "acf": acf_data,
            }
            
            console.info(f"Residuals analysis: mean={residuals_mean:.4f}, std={residuals_std:.4f}")
            
            return analysis
            
        except Exception as e:
            console.warn(f"Could not analyze residuals: {e}")
            return {}

    def get_diagnostics(self) -> dict:
        """Return model diagnostics for visualization"""
        return self.model_info

