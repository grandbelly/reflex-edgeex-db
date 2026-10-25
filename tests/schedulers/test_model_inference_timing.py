"""
Tests for model.predict() and pickle.loads timeout guards.

Validates that ForecastScheduler.generate_predictions:
1. Raises asyncio.TimeoutError cleanly (NOT hang) when a synchronous
   "async def" plugin's predict() blocks longer than MODEL_PREDICT_TIMEOUT.
2. Falls back to the persistence model without crashing the cycle.
3. Does NOT freeze the event loop while a slow predict is running -
   other coroutines must continue to make progress.

Run:
    pytest tests/schedulers/test_model_inference_timing.py -v
"""

from __future__ import annotations

import asyncio
import time

import pytest

from edgeex_app.schedulers import forecast_scheduler as fs_mod
from edgeex_app.schedulers.forecast_scheduler import ForecastScheduler


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeSlowSyncAsyncPredictModel:
    """
    Mimics edgeex_app/ml/pipeline_v2_hybrid.py plugins: `predict` is declared
    `async def` but its body is purely synchronous (uses time.sleep, NOT
    asyncio.sleep). On the unpatched code this blocks the event loop.
    """

    def __init__(self, sleep_seconds: float):
        self._sleep_seconds = sleep_seconds

    async def predict(self, horizon: int):
        import pandas as pd  # local import keeps top-level import-time cheap
        time.sleep(self._sleep_seconds)  # SYNC sleep, blocks executor thread
        # Return a minimally-valid AutoARIMA-shaped frame
        return pd.DataFrame({
            "AutoARIMA": [42.0] * horizon,
            "AutoARIMA-lo-95": [40.0] * horizon,
            "AutoARIMA-hi-95": [44.0] * horizon,
        })


class FakeFastSyncAsyncPredictModel:
    """Sub-millisecond fake - control case."""

    async def predict(self, horizon: int):
        import pandas as pd
        return pd.DataFrame({
            "AutoARIMA": [1.0] * horizon,
            "AutoARIMA-lo-95": [0.9] * horizon,
            "AutoARIMA-hi-95": [1.1] * horizon,
        })


# ---------------------------------------------------------------------------
# Test 1 - Timeout raises cleanly + falls back
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_predict_timeout_falls_back_to_persistence(monkeypatch):
    """
    With MODEL_PREDICT_TIMEOUT set very low and a model whose predict()
    sleeps 2s, generate_predictions must:
      - NOT hang
      - NOT raise out of generate_predictions
      - Return a persistence-model fallback dict
    """
    monkeypatch.setattr(fs_mod, "MODEL_PREDICT_TIMEOUT_SECONDS", 0.3)

    scheduler = ForecastScheduler()
    horizons = [60, 120, 360]
    last_value = 100.0
    slow_model = FakeSlowSyncAsyncPredictModel(sleep_seconds=2.0)

    t0 = time.perf_counter()
    result = await scheduler.generate_predictions(
        model=slow_model,
        model_type="AUTO_ARIMA",
        last_value=last_value,
        horizons=horizons,
    )
    elapsed = time.perf_counter() - t0

    # Must come back within ~1s (timeout 0.3s + scheduling overhead)
    assert elapsed < 1.5, (
        f"generate_predictions hung for {elapsed:.2f}s - "
        f"timeout guard is not working"
    )

    # Must be persistence-model fallback (all values == last_value)
    assert result["predictions"] == [last_value] * len(horizons)
    # CI is +/-5% of last_value in the fallback branch.
    # Use abs-diff comparison to avoid pytest.approx triggering numpy
    # array detection (which can hit a circular-import edge case on
    # Windows + pandas + numpy combos seen in CI).
    for got, expected in zip(result["ci_lower"], [last_value * 0.95] * len(horizons)):
        assert abs(got - expected) < 1e-9
    for got, expected in zip(result["ci_upper"], [last_value * 1.05] * len(horizons)):
        assert abs(got - expected) < 1e-9


# ---------------------------------------------------------------------------
# Test 2 - Event loop stays responsive while predict is slow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_other_coroutines_progress_during_slow_predict(monkeypatch):
    """
    While one model's predict() is sleeping synchronously, an independent
    background coroutine awaiting asyncio.sleep(0.05) in a loop must keep
    ticking. Pre-fix, the time.sleep inside `async def predict()` would
    freeze the event loop and the ticker would not progress until predict
    returned. Post-fix, predict runs in the thread pool and the loop is
    free.
    """
    # Allow predict() to finish (1.0s) WITHIN the timeout window (3.0s),
    # so we can prove both that (a) the loop kept ticking and (b) the
    # patched call still returns the model's data on success.
    monkeypatch.setattr(fs_mod, "MODEL_PREDICT_TIMEOUT_SECONDS", 3.0)

    scheduler = ForecastScheduler()
    horizons = [60, 120, 360, 720, 1440]
    last_value = 100.0
    slow_model = FakeSlowSyncAsyncPredictModel(sleep_seconds=1.0)

    ticks = []

    async def background_ticker():
        for _ in range(20):  # 20 * 0.05s = 1s of wall clock potentially
            await asyncio.sleep(0.05)
            ticks.append(time.perf_counter())

    # Run predict and ticker concurrently
    t0 = time.perf_counter()
    ticker_task = asyncio.create_task(background_ticker())
    predict_result = await scheduler.generate_predictions(
        model=slow_model,
        model_type="AUTO_ARIMA",
        last_value=last_value,
        horizons=horizons,
    )
    await ticker_task
    total_elapsed = time.perf_counter() - t0

    # While predict was running (~1s), ticker should have accumulated
    # at least ~10 ticks. If the loop was frozen we'd see ticker only
    # starting AFTER predict returns - i.e. all ticks would be clustered
    # at the end.
    assert len(ticks) == 20, f"ticker should complete: got {len(ticks)} ticks"
    ticks_during_predict = [t for t in ticks if t - t0 < 0.95]
    assert len(ticks_during_predict) >= 8, (
        f"event loop appears frozen during predict - only "
        f"{len(ticks_during_predict)}/20 ticks landed in the first 0.95s "
        f"(expected >= 8 if the loop is not blocked)"
    )

    # predict result is the real one, NOT persistence fallback
    assert predict_result["predictions"] == [42.0] * len(horizons), (
        "predict should have succeeded within the timeout; got: "
        f"{predict_result['predictions']}"
    )

    # Total elapsed should be close to max(predict_time, ticker_time) = ~1s,
    # not sum.
    assert total_elapsed < 2.0, (
        f"concurrent run took {total_elapsed:.2f}s - "
        f"work was serialized instead of concurrent"
    )


# ---------------------------------------------------------------------------
# Test 3 - Sanity: fast model still works
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fast_model_works_normally(monkeypatch):
    monkeypatch.setattr(fs_mod, "MODEL_PREDICT_TIMEOUT_SECONDS", 5.0)
    scheduler = ForecastScheduler()
    result = await scheduler.generate_predictions(
        model=FakeFastSyncAsyncPredictModel(),
        model_type="AUTO_ARIMA",
        last_value=10.0,
        horizons=[60, 120],
    )
    assert result["predictions"] == [1.0, 1.0]
