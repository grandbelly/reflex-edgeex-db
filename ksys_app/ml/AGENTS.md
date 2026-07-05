# ksys_app/ml — time-series forecasting

## Purpose

Multi-horizon water-quality forecasts (1h/2h/6h/12h/24h) via swappable statistical + ML models.
Covers training, inference, persistence, drift detection, and prediction intervals.

## Ownership

Key files: `pipeline_v2_hybrid/training.py` (TrainingPipelineV2, walk-forward CV),
`pipeline_v2_hybrid/plugins/{autoarima,prophet,xgboost}.py`, `forecast_pipeline.py` (preprocess→train/predict),
`ensemble_model.py`/`ensemble_plugin.py`, `prediction_model.py` (TimeSeriesPredictor),
`drift_detector.py`, `prediction_intervals.py`.

## Local Contracts

- **Plugin architecture**: every model extends the `ModelPlugin` ABC (async `train`/`predict`); resolve via
  `ModelRegistry.get(model_type)`. Add a model by adding a plugin + registering it — don't fork the pipeline.
- **Persistence**: pickled model in the `forecasting_models` DB table (primary); `./saved_models/` joblib is
  legacy fallback only.
- **Timeout guards**: `FORECAST_PICKLE_LOAD_TIMEOUT` (15s), `FORECAST_MODEL_PREDICT_TIMEOUT` (45s) — never
  remove; they stop a hung model from blocking the scheduler.
- Deps: `statsforecast`, `scikit-learn`, `joblib`, `pandas`, `numpy`. Same lazy-import discipline as `ai_engine`.

## Work Guidance

- New model type = new `ModelPlugin` subclass under `pipeline_v2_hybrid/plugins/` + registry entry.
- Training fits with `TimeSeriesSplit` CV; inference is called by `ForecastScheduler` (see `schedulers/`).

## Verification

`pytest`; validate forecasts against held-out actuals (MAE/RMSE) — `PerformanceAggregator` does this online.

## Child DOX Index

None — `pipeline_v2_hybrid/` and its `plugins/` are governed by this contract.
