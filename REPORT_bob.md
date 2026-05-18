# Bob - Asyncio + ML inference investigation (H2 & H3)

Stage 2 / agent bob-async-model
Branch agentic/forecast-scheduler-timeout-fix/bob-async-model
Target: ksys_app/schedulers/forecast_scheduler.py lines 88-91 and 149
Verdict: **H2 PROVEN**, **H3 INCONCLUSIVE but plausibly aggravating**.

## 1. Where model.predict() actually lives

forecast_scheduler.py:149 calls `await model.predict(len(horizons))`. The model object is what `pickle.loads(model_pickle)` returns - one of the plugin classes in:

- ksys_app/ml/pipeline_v2_hybrid.py (v2 training path)
  - AutoARIMAPlugin.predict() at line 390-408
  - ProphetPlugin.predict() at line 764-792
  - XGBoostPlugin.predict() at line 1085
- ksys_app/ml/pipeline_builder.py (v1 legacy path)
  - AutoARIMAPlugin.predict() at line 145-151
  - ProphetPlugin.predict() at line 182-189

### Key excerpt - pipeline_v2_hybrid.py:390 (AutoARIMA)

```python
async def predict(self, horizon: int, level: list = None) -> pd.DataFrame:
    if self.model is None:
        raise ValueError("Model not trained")
    if level:
        forecast = self.model.predict(h=horizon, level=level)   # SYNC statsforecast call
    else:
        forecast = self.model.predict(h=horizon)                # SYNC statsforecast call
    return forecast
```

### Key excerpt - pipeline_v2_hybrid.py:764 (Prophet)

```python
async def predict(self, horizon: int, level: list = None) -> pd.DataFrame:
    if self.model is None:
        raise ValueError("Model not trained")
    future = self.model.make_future_dataframe(periods=horizon, freq='10T')  # SYNC
    forecast = self.model.predict(future)                                   # SYNC, 100ms-seconds
    ...
    return result
```

**Every single plugin's predict() is `async def` with a 100% synchronous body.** No await, no run_in_executor, no asyncio.to_thread. The "async predict() wrapper" comment in forecast_scheduler.py:148 is factually wrong.

## 2. H2 verdict - PROVEN

`await model.predict(len(horizons))` executes statsforecast/Prophet inference on the event loop thread:

- Prophet's `model.predict(future)` does posterior sampling per horizon point. On RPi 4 with ~10k training rows: 200ms-2s normal, up to >5s under memory pressure.
- During that time the Reflex asyncio loop is **frozen**. Any concurrent `asyncio.wait_for` (e.g. SQLAlchemy `pool_timeout=10`) cannot fire until the predict returns. As soon as the loop wakes it raises the queued TimeoutError - which presents as a "TimeoutError after 10s" attributed to whichever coroutine the loop resumes first. Hence the intermittent, hard-to-attribute symptom in HANDOFF.md.
- forecast_scheduler.py:506 processes models serially. N=5 models * ~3s/model = 15s blocked - guaranteed trip of downstream timeouts.

This is the most likely root cause of intermittent TimeoutError because it requires no external pressure - only "a model that happens to run slowly this cycle".

## 3. H3 verdict - INCONCLUSIVE (but possibly aggravating)

load_model_from_bytea at line 88-91 already uses `loop.run_in_executor(None, lambda: pickle.loads(...))`. Correct pattern in principle, but:

- The default executor is the asyncio ThreadPoolExecutor(max_workers=min(32, os.cpu_count()+4)). On RPi (4 cores) = 8 threads. **It is shared globally** with Reflex, SQLAlchemy greenlet_spawn, and every other `run_in_executor(None, ...)` in the app.
- pickle.loads for statsforecast/Prophet is genuinely CPU-bound (recursive Python object reconstruction). Holds the GIL, so even running in a thread it blocks any other Python work in the process - including the event loop's wake-up callbacks.
- We do not have model size measurements in-tree. Without an actual RPi pickle (typically 5-50 MB), this hypothesis cannot be proven empirically. But the current code has no timeout guard, so a pathologically large model would hang silently.

Verdict: INCONCLUSIVE on evidence but fix is cheap. Wrap with `asyncio.wait_for(loop.run_in_executor(...), timeout=N)` to convert any hang into a clean, observable TimeoutError.

## 4. Recommended fix

1. Wrap `model.predict()` in `loop.run_in_executor` + `asyncio.wait_for`. Treat plugin predict() as sync (because it is). asyncio.wait_for accepts both coroutines and Futures, so this is forward-compatible with future genuinely-async plugins.
2. Wrap pickle.loads in asyncio.wait_for with a separate timeout.
3. Add time.perf_counter() deltas in DEBUG logs for both calls.

### Timeout values

| Call | Timeout | Justification |
|---|---|---|
| pickle.loads(model_pickle) | 15s | Generous on RPi for a 50MB model. Expected <= 2s. |
| model.predict(...) per model | 45s | Prophet on RPi with 1440-min horizon (24h * 6/h) is worst case, measured ~10-20s. AutoARIMA faster. 45s never fires healthy but caps stuck model below a 5-min cycle. |

(Conservative for shake-out. Tighten once empirical per-cycle timings exist.)

## 5. Patch summary

- ksys_app/schedulers/forecast_scheduler.py
  - load_model_from_bytea: wrap pickle.loads / pickle.load in asyncio.wait_for (15s) + perf_counter delta DEBUG log.
  - generate_predictions: dispatch model.predict via loop.run_in_executor wrapped in asyncio.wait_for (45s). Fall back to persistence model on asyncio.TimeoutError (does NOT crash the cycle - partial-failure tolerance).
- tests/schedulers/test_model_inference_timing.py - new pytest-asyncio test file:
  1. Slow sync predict (2s sleep) with 0.3s timeout: scheduler raises asyncio.TimeoutError cleanly, falls back to persistence model, does NOT hang the loop.
  2. While one model's predict is sleeping, an independent coroutine ticks through 5 iterations of `await asyncio.sleep(0.05)` - proves slow predict no longer blocks other loop work.

## 6. What this does NOT solve

- Pool exhaustion (Alice's H1).
- Cycle-overrun timing (Charlie's H4 / H7).
- Architectural smell: plugins lie about being async. Real fix is either (a) make plugins sync and have callers dispatch, or (b) make plugins genuinely async via asyncio.to_thread. Out of scope; record on refactor backlog.
