# KSys IoT — Code Quality Audit (states/)

Date: 2026-05-21
Scope: `ksys_app/states/**`, with cross-references into `ksys_app/schedulers/**` and `ksys_app/services/**`.
Method: structural grep + targeted reads. No code executed.

Baseline metrics (states/ only):
- 31 state files, 725 function/method definitions, 284 occurrences of `async with self:`, 117 `@rx.event(background=True)`, 46 untyped `dict`/`list` annotations, 101 generic `except Exception as e:` blocks.
- `training_state/state.py` = 1,077 LoC (already flagged by verify-deep1).
- 7 `.backup`/`.bak`/`_OLD`/`.disabled` files still in tree (dead code).

---

## 1. `save_model` — Concern-Separation Map (state.py L712–1022, 311 LoC)

| Step | Lines | Concern | Notes |
|------|-------|---------|-------|
| Setup | 715–717 | UI flag + error reset | Inside `async with self:` |
| 1. Pickle | 728–748 | Serialize model from module cache → BYTEA | `_get_cached_model` lookup, `pickle.dumps`, swallowed exception (warn only) |
| 1.5 Timestamps | 750–754 | Generate `current_time` + version string | `current_time` is **re-computed at L887** (bug-adjacent: dup) |
| 2. Datetime parsing | 756–778 | `data_start_str` / `data_end_str` → datetime | Two near-identical try/except blocks |
| 3. Feature config lookup | 780–797 | Service call to map name → id | Uses `FeatureConfigService(session)` — needs ORM session, fine here |
| 3.5 Build `pipeline_config` dict | 799–831 | Pure data assembly | 32-line literal; could be a builder method on a config dataclass |
| Logging block | 833–847 | 14 `console.info` calls | Pure side-effect, mixed with data prep; noisy on RPI |
| 4. ORM insert (ModelRegistry) | 849–879 | DB write (single row) | `session.add` + `flush` |
| 5. Bulk insert evaluation rows | 881–928 | Raw SQL INSERT in a Python for-loop | **N+1 INSERT** — see §3 |
| Commit | 930 | session.commit | |
| 6. Verification SELECT | 935–960 | Re-read what we just wrote | ORM + raw SQL mixed in same block |
| UI signals | 962–1010 | `async with self:` updates + toast | Re-builds dict from `saved_model` row, list-comp from `saved_preds` |
| Error path | 1012–1021 | Generic exception + toast | `is_loading=False` not in a `finally` |

**Verdict:** Not spaghetti — it is sequentially organized like `start_training` — but it is a **God-method** with 7 distinct concerns. Severity **HIGH** for maintainability and RPI memory (entire trained model held in memory through pickle + flush + 36 INSERTs + verification SELECT all in one session scope).

**Specific issues (file:line · severity · fix):**

| Severity | Loc | Issue | Suggested fix |
|---|---|---|---|
| HIGH | L905–926 | Per-prediction `await session.execute(insert_sql, {...})` inside `for i, value in enumerate(self.forecast_values)`. 36 round-trips for default 6h@10min config | Use `session.execute(insert_sql, [params1, params2, ...])` (executemany) or `INSERT ... VALUES (...), (...), ...` constructed once |
| HIGH | L729 + L754 | `datetime.now()` called twice → `model_name` and `version` can disagree by ~ms | Compute once into `current_time`, derive both from it |
| MED | L744–746 | `except Exception` swallows pickle failure with only a warn; model gets saved as metadata-only without surfacing to UI | Add to `error_message` or yield a toast warning |
| MED | L887 | `current_time = datetime.now()...` re-assigned, shadowing L751 — silent timestamp drift between ModelRegistry row and evaluation rows | Reuse L751 value |
| MED | L884, L936 | `from sqlalchemy import text` / `select` imported inside the method | Move to module top |
| MED | L721–726 | 5 inner imports (`ModelRegistry`, `Prediction`, `datetime`, `json`, `os`, `pickle`, `Path`); `Prediction`, `os`, `Path` are unused | Remove unused, hoist others |
| LOW | L833–847 | 14 `console.info` per save call → spam on RPI | Collapse to 1–2 structured logs |
| LOW | L1014 vs L719 | `is_loading=False` only inside try-success and except. If `async with get_async_session()` raises before try-body executes there's no cleanup | Use `try/finally` for `is_loading` reset |
| LOW | L967–998 | 80 lines of dict/list construction inside `async with self:` lock | Build outside, assign inside |

---

## 2. Other state files — oversized methods, god-classes, copy-paste

### Oversized methods (>100 LoC)

| File | Method | Lines | LoC | Severity |
|------|--------|-------|-----|----------|
| `forecast_player_state/state.py` | `_load_predictions_internal` | 1077–1238 | **161** | HIGH |
| `forecast_player_state/state.py` | `_load_playlist_internal` | 991–1076 | 85 | MED |
| `dashboard_realtime.py` | `_fetch_data` | 130–306 | **176** | HIGH |
| `dashboard\state.py` | `load` | 231–898 | **667** | CRITICAL |
| `dashboard\state.py` | `start_realtime` | 1133–1193 | 60 | MED |
| `dashboard\state.py` | `_update_kpi_unified_from_realtime` | 1331–1499 | **168** | HIGH |
| `dashboard\state.py` | `_update_series_with_realtime` | 1500–1562 | 62 | MED |
| `dashboard_realtime_grouped.py` | `_fetch_grouped_data` | 227–292 | 65 | MED |
| `alarm_state.py` | `load_alarm_events` | 45–181 | 136 | HIGH |
| `alarm_state.py` | `search_similar_alarms` | 438–525 | 87 | MED |
| `model_performance_state.py` | `load_all_saved_models` | 392–500 | **108** | HIGH |
| `model_performance_state.py` | `algorithm_comparison_data` (@rx.var) | 682–784 | 102 | HIGH (computes every render) |
| `model_performance_state.py` | `training_conditions_match` | 850–899 | 49 | MED |
| `alarm_hist_state.py` | `fetch_history` | 120–213 | 93 | MED |
| `communication_state.py` | `heatmap_matrix` (@rx.var) | 104–157 | 53 | HIGH (pandas pivot every render) |
| `communication_state.py` | `_fetch_data` | 388–442 | 54 | MED |
| `viewer_tag_state.py` | (16 background event handlers, mostly OK) | — | — | LOW |

### God classes

| File | Class | Method count | Issue |
|------|-------|--------------|-------|
| `dashboard\state.py` | `DashboardState` | 68 methods, 1635+ lines | Mixes loading, KPI calc, chart computation, realtime updates, navigation, dialog state. **CRITICAL refactor target.** |
| `forecast_player_state\state.py` | `ForecastPlayerState` | 83 methods | Mixes data loading, chart formatting, table row builders, countdown timer, scheduler triggers |
| `training_state\state.py` | `TrainingState` | 27 methods + start_training/save_model | Already known; biggest pain points covered in §1 |
| `model_performance_state.py` | `ModelPerformanceState` | 37 methods | Loading + recommendation + deploy + delete + view-model formatters all in one class |
| `alarms.py` | `AlarmsState` | 37 methods | Pagination, filter, view-mode, selection, ack — split into mixins |

### Copy-paste / parallel files (DRY violations across state files)

| Pair | Evidence | Severity |
|------|---|---|
| `base.py` vs `base_state.py` | Two parallel `BaseState` classes (L10 vs L12). Both define `toggle_sidebar`, `toggle_theme`, refresh polling. Different children import from different ones → divergent behavior | HIGH |
| `trend_state.py` vs `trend_state_enhanced.py` | `load_series_data` (T:96 / TE:94), `_parse_time_range`, `_get_aggregation_table`, `_get_time_range_options`, `export_csv_all/page`, `series_for_tag_desc_with_num_all`, `y_axis_domain`, all paging vars — ~90% identical. Only difference: TE uses `selected_tags[0]` + inherits `TagHierarchyState` | HIGH |
| `dashboard_realtime.py` vs `dashboard_realtime_grouped.py` vs `dashboard_realtime_OLD.py` | Three parallel realtime dashboards; `_OLD` still on disk | MED |
| `training_wizard_state.py` vs `training_wizard_state_plotly_backup.py` | Backup file checked in (593 vs ~470 LoC, very similar) | MED |
| `alarm_state.py` / `alarm_rt_state.py` / `alarm_hist_state.py` / `alarms.py` / `alarms_enhanced.py` / `scada_alarm_state.py` / `scada_alarm_comparison_state.py` | **7 parallel alarm states**. Each has its own filter/severity/level/page logic. No shared `AlarmFilterMixin` | HIGH |
| `dashboard_realtime_OLD.py`, `dashboard_realtime_grouped.py:293 stop_streaming` duplicated, `alarm_rt_state.py:133 + 272 toggle_auto_refresh` defined twice in the same class (L133, L272) | Real bug: second def overrides first silently | HIGH |

### Dead / backup files in tree (delete candidates)

```
ksys_app/states/dashboard_realtime_OLD.py                            226 LoC
ksys_app/states/training_wizard_state_plotly_backup.py               ~470 LoC
ksys_app/pages/communication_new_backup.py
ksys_app/pages/training_wizard_plotly_backup.py
ksys_app/pages/trend_enhanced.py.bak
ksys_app/pages/trend_improved.py.bak
ksys_app/pages/trend_enhanced_v2.py.disabled
ksys_app/ksys_app.py.backup_20250918_211659
```
Severity **MED** — confuses imports, bloats RPI image.

---

## 3. N+1 query patterns

Direct N+1 found (await DB call inside a loop):

| File | Line | Pattern | Severity |
|------|------|---------|----------|
| `training_state/state.py` | 905–926 | `for i, value in enumerate(self.forecast_values): await session.execute(insert_sql, {...})` — 36+ INSERTs per save_model | HIGH |
| `schedulers/forecast_scheduler.py` | 391 | `for tag in tags: async with get_async_session()` (verified by re-grep with context) — opens a fresh session per tag inside scheduler tick | HIGH |
| `viewer_tag_state.py` | toggle_dashboard/alarm/trend/model (L109/126/143/160) | Each toggle reopens `get_async_session()` instead of batching | MED |
| `ai_state.py` | L57, L124, L136, L179, L199 | 5 `async with get_async_session()` blocks in `send_message` flow per single user message | MED |

**Not** N+1 but smell: `forecast_player_state/state.py:1093–1184` opens one session and runs 3 sequential `session.execute()` (rolling window, latest sensor, forecast_time, range_query) — could be a single CTE.

`async with get_async_session()` total: **66 call sites** across the codebase (file rollup above). A session-per-method discipline is fine in app code; the problem is the **loops** above and the **lack of a `@with_session` decorator** so every method re-implements the boilerplate.

---

## 4. Magic numbers — constants module candidates

These literals are scattered across state/scheduler/service files with no central definition. Recommend `ksys_app/constants/forecast.py` etc.

| Constant | Current locations | Suggested name |
|---|---|---|
| `10` (forecast interval minutes) | `training_state/state.py:52`, `forecast_scheduler.py:347,743`, `forecast_service.py:251`, `pipeline_builder.py:281` | `FORECAST_INTERVAL_MIN` |
| `6` (forecast horizon hours), `360` (6h in min) | `training_state/state.py:53`, `training_state/state.py:99` | `FORECAST_HORIZON_HOURS_DEFAULT`, `FORECAST_HORIZON_MIN_DEFAULT` |
| `30` (lookback intervals / training days) | `training_state/state.py:46`, `forecast_player_state/state.py:1099`, `forecast_scheduler.py:473`, `forecast_service.py:243`, `daily_training.py:34,433` | `TRAINING_DAYS_DEFAULT`, `ROLLING_WINDOW_LOOKBACK` |
| `24` (default forecast horizon legacy) | `training_state/state.py:47`, `alarms.py:41,421,423`, `alarms_enhanced.py:41`, `forecast_scheduler.py:479`, `forecast_service.py:587`, `trend_service.py:161`, `feature_engineering_service.py:76,374` | `LEGACY_FORECAST_HORIZON_HOURS`, `ALARMS_DEFAULT_HOURS` (split by domain) |
| `600` (seconds = 10min countdown) | `forecast_player_state/state.py:56,57,1228` | `FORECAST_COUNTDOWN_SEC` |
| `5000` (chart max points) | `trend_state.py:130`, `trend_state_enhanced.py:126` | `TREND_MAX_POINTS` |
| `100` (batch size) | `actual_value_updater.py:54`, `response_optimizer.py:258` | `DB_BATCH_SIZE` |
| `20`/`25` (page sizes) | `alarms.py:49`, `alarms_enhanced.py:49`, `alarm_hist_state.py:56`, `alarm_service.py:28,217` | `ALARMS_PAGE_SIZE`, `ALARM_HIST_PAGE_SIZE` |
| `15`/`30` (refresh intervals seconds) | `base.py:18`, `dashboard_realtime.py:44`, `dashboard_realtime_grouped.py:40`, `dashboard_realtime_OLD.py:35`, `base_state.py:17` | `DEFAULT_REFRESH_INTERVAL` (and one per page) |
| `3.0` (outlier threshold) | `training_state/state.py:49`, `model_performance_state.py:480` | `OUTLIER_THRESHOLD_DEFAULT` |
| `'Asia/Seoul'` (timezone string) | 30+ call sites across states | `from ksys_app.constants import KST` |

Severity **MED** — none is a bug today, but RPI multi-deploy requires per-site overrides (e.g., 5min vs 10min interval), and without constants you grep 12 files.

---

## 5. Type hint quality

Sampled across `ksys_app/states/` (725 def sites):

| Metric | Count |
|---|---|
| Total def/async def | 725 |
| Untyped `dict` / `list` / `-> dict` / `-> list` / `dict[str, Any]` / `list[dict]` | 46 distinct file matches; full grep across `ksys_app/states/` produced **>120 individual annotations** of the form `dict` / `list` without parametrization |
| `Dict[str, Any]` (any container) | Pervasive — `ai_state.py:225,272,298,303,308,353,358,363,368,373,383,388,393`, `model_performance_state.py:125,165,193,222,251,327,672,682,952`, `forecast_player_state/state.py:93,128,167,184,261,300,502` |
| Untyped method params (esp. `set_*` handlers) | `dashboard\state.py:899,1003,1007,1011,1015,1020`: `def set_show_avg(self, v: object)` — `object` is effectively untyped; the value is always `bool \| str` from Reflex checkbox |
| Functions with no return annotation | Numerous (e.g., `model_recommendation.py:10,22,34,77` all `-> Dict[str, Any]` — at least annotated; but `dashboard\utils.py:12 _to_float(v: Any)` is `Any` in/out) |

| Severity | Issue | Fix |
|---|---|---|
| MED | Heavy use of `Dict[str, Any]` for service return types (esp. `model_performance_state.py`, `ai_state.py`) | Define `TypedDict` per response shape; pydantic models in `services/` |
| MED | `forecast_player_state/state.py` row builders return `List[Dict]` with implicit schema (e.g., `chart_data_with_errors`, `table_data_rows`) | TypedDict for each table row schema |
| LOW | `dashboard\state.py` setter params typed `object` | Use `bool` (and let Reflex's CheckedState coerce) or accept `bool \| list[str]` explicitly as elsewhere |

---

## 6. DRY violations beyond progress boilerplate

### 6.1 Progress boilerplate (already known from verify-deep1)

`async with self: self.training_progress = N; self.training_status = "..."; yield` appears **17 times** in `start_training` alone (counted via the grep: L368/374/381/387/403/414/420/432/444/472/487/503/513/526/542/557/573/582/605/620/665).

Helper recipe (add to `TrainingState` or a `ProgressMixin`):
```python
async def _set_progress(self, pct: int, status: str):
    async with self:
        self.training_progress = pct
        self.training_status = status
        yield
```

### 6.2 Validation guards — repeated 3× at top of `start_training` (L367–384)
Three identical `if not X: async with self: self.error_message = ...; yield; return` blocks. Replace with:
```python
errors = self._validate_inputs()
if errors:
    async with self: self.error_message = errors; yield
    return
```

### 6.3 Try/except shape — `async with self: self.error_message = str(e); self.loading = False`

Found **101 generic `except Exception as e:` blocks** across 24 state files. Almost all share the shape:
```python
except Exception as e:
    console.error(f"... failed: {e}")
    async with self:
        self.error_message = str(e)
        self.loading = False  # or is_training=False, is_loading=False
```
**Fix:** A decorator on event handlers:
```python
@background_event_with_error_handling(loading_field="is_loading")
async def save_model(self): ...
```
This single change removes ~30 lines per state file × 24 files ≈ 700 LoC and ensures `loading` is always reset.

### 6.4 DB session boilerplate

```python
async with get_async_session() as session:
    service = XService(session)
    result = await service.method(...)
```
Repeated **~66 times**. A `@with_service(XService)` decorator (or `async def _with(self, service_cls, fn)` helper) would shrink each event handler.

### 6.5 Parallel scheduler vs state logic

| Scheduler | State doing the same thing |
|---|---|
| `forecast_scheduler.py:467 (write_prediction)` | `training_state/state.py:881–928` (writes near-identical rows to `training_evaluation` instead of `predictions` — schema drift risk) |
| `actual_value_updater.py:53,139` | `forecast_player_state/state.py:_load_predictions_internal:1136` recomputes MAE/MAPE/RMSE on the client side from rolling window, while the updater is supposed to populate them in `prediction_performance`. **Two sources of truth.** |
| `daily_training.py` | `training_state/state.py:start_training` — same pipeline, different call sites, no shared `TrainingFacade` |

Severity **HIGH** for the predictions vs training_evaluation split (see §1, L881 comment "NOT predictions table"). One day a column added to predictions will not get added to training_evaluation. Recommend a single `evaluation_insert(session, rows, target_table)` helper.

### 6.6 JSON parsing boilerplate (HIGH)

`model_performance_state.py:425–445` and similar pattern in `forecast_player_state/state.py` (parsing `hyperparameters`/`pipeline_config` that may be `str` or `dict`) is repeated 5+ times:
```python
if isinstance(rec.hyperparameters, str):
    try: hyperparams = json.loads(...)
    except: hyperparams = {}
elif isinstance(rec.hyperparameters, dict):
    hyperparams = rec.hyperparameters
```
Fix: Single `_safe_json(value, default={})` helper. Bonus: fix the ORM column to be `JSONB` so it's always `dict` — eliminates the branch entirely.

### 6.7 Duplicate method definition (real bug)

`alarm_rt_state.py:133` and `alarm_rt_state.py:272` both define `def toggle_auto_refresh(self)`. Python keeps the **second** silently. Verify intended behavior. Severity **HIGH** (correctness).

---

## 7. Reflex-specific anti-patterns

| Severity | File:Line | Issue | Fix |
|---|---|---|---|
| HIGH | `training_state/state.py:395–700` | `start_training` (338 LoC) runs the **entire ML pipeline** (`await pipeline.execute()` at L508 — minutes of CPU on RPI) inside the outer `try` block of a background event. While it does `yield` between steps, the heavy `pipeline.execute()` itself is inside `try` not under `async with self:` — that's actually correct. But the **17 `async with self:` short critical sections** mean Reflex acquires the state lock 17 times per training, each time blocking other UI events. Consider `asyncio.Lock` only for the final commit. | Reduce to 3 progress checkpoints (start, mid, end); collapse intermediate `yield`s |
| HIGH | `training_state/state.py:715–1010` (`save_model`) | Marked `@rx.event(background=True)` ✅ but **`pickle.dumps(trained_model)` at L741 runs while NOT inside `async with self:` ✅ good** — but it's also not in an executor. On RPI, pickling a 10MB ARIMA model on the asyncio event loop blocks all other I/O for hundreds of ms | Wrap `pickle.dumps` in `await asyncio.get_event_loop().run_in_executor(None, pickle.dumps, model)` |
| HIGH | `communication_state.py:104 heatmap_matrix` (`@rx.var`) | Pandas pivot computed on every state change. `@rx.var` should be O(1) or memoized; pandas pivot is O(n) | Cache result in regular field, recompute only when `_df_hourly` changes |
| HIGH | `model_performance_state.py:682 algorithm_comparison_data` (`@rx.var`, 102 LoC) | Same — runs on every render | Move to event handler, store in field |
| MED | `dashboard\state.py:231 load` (667 LoC) | Almost certainly missing `background=True` on something this slow. Need to verify the decorator (could be applied above L231 — not shown). If missing, will freeze UI | Inspect L230 for `@rx.event(background=True)` |
| MED | `alarms.py:25 background events`, with 11 large state vars per state | `AlarmsState` has 25 background handlers but state vars like `self.alarms` (list[Dict]), `chart_data` etc. are **large lists serialized on every state change**. Reflex sends full state diff over WS. | Split into `AlarmsListState` + `AlarmsFilterState` + `AlarmsStatsState` (SubStates) |
| MED | `dashboard\state.py` ~68 `@rx.var` computed properties + 27 setters → 95 reactive bindings on one state | Each subscription triggers diff calc. | Split into `DashboardFilterState`, `DashboardChartState`, `DashboardKPIState` |
| MED | `forecast_player_state/state.py:1606–1620 (countdown loop)` | `self.countdown_seconds -= 30` inside what looks like a polling loop. Tight loops that mutate state every iteration should use `rx.var` + server-side time, not store the countdown in state | Compute countdown from `latest_forecast_time` in an `@rx.var` |
| MED | `alarm_rt_state.py:272` duplicate `toggle_auto_refresh` | (Same as §6.7) | Delete one |
| LOW | `training_state/state.py:962–1010` | 48-line dict/list construction inside `async with self:` lock — holds the state lock for hundreds of ms while building Python objects | Build outside, assign inside |

---

## Cross-cutting recommendations

1. **Constants module** (`ksys_app/constants/`) — pulls out 12+ scattered magics (§4). Pre-req for RPI-per-site config.
2. **`@event_with_error(loading_field=...)` decorator** — kills ~100 try/except blocks (§6.3). Single change with massive surface area.
3. **`@with_session` / `@with_service(XService)`** — kills 66 session-open boilerplate blocks (§6.4).
4. **Delete dead files** (§2) — instant 1500+ LoC reduction; clarifies which `BaseState` and `DashboardRealtime*` is real.
5. **Single `BaseState`** — pick `base.py` or `base_state.py`, delete the other, migrate imports.
6. **Bulk INSERT in `save_model`** — single biggest perf win on save (§3 / §1).
7. **Split god-classes** into SubStates — esp. `DashboardState` (68 methods), `ForecastPlayerState` (83 methods).
8. **DEPRECATED `forecast_horizon` field** (`training_state/state.py:47`) — still used as fallback at L610. Remove fallback, then remove field, then run migrations.

---

## Top 5 highest-impact fixes (impact × effort⁻¹)

| # | Fix | Impact | Effort | Files touched | Why now |
|---|-----|--------|--------|---------------|---------|
| 1 | Delete dead/backup files (`*_OLD.py`, `*_backup.py`, `.bak`, `.disabled`) | HIGH (clarity, RPI image size, kills divergent BaseState confusion) | XS (< 1h) | 8 files | Zero-risk; unblocks all subsequent refactors by removing ambiguous imports |
| 2 | `@event_with_error(loading_field=...)` decorator for the 101 `except Exception as e: async with self: self.error_message = ...` patterns | HIGH (~700 LoC removed, guarantees `loading` reset on every error path) | S (1 day, 24 files) | All states/ | Highest LoC/hour ratio. Also fixes silent `is_loading=True` lock-ups |
| 3 | Bulk INSERT in `save_model` (L905–926) + move `pickle.dumps` to executor (L741) | HIGH on RPI (36 round-trips → 1; un-blocks event loop during pickle) | S (2h, 1 file) | `training_state/state.py` | Directly hits the user-visible "save is slow" symptom |
| 4 | Extract `ksys_app/constants/` (forecast.py, alarms.py, refresh.py) and replace 12+ magic numbers | MED-HIGH (enables per-RPI overrides via env, eliminates silent drift) | S (3h, ~20 files) | states/, schedulers/, services/ | Prerequisite for "deploy to multiple RPIs" plan — each site can tune intervals without code edits |
| 5 | Merge `trend_state.py` ↔ `trend_state_enhanced.py` (90% duplicate) and consolidate the 7 alarm states behind an `AlarmFilterMixin` | HIGH (≈ 1000 LoC removed, single source for filter/pagination logic) | M (1–2 days) | states/ | Sets pattern for further god-class splits; biggest DRY win after #2 |

### Honorable mention (don't fit in top 5 but cheap)

- Fix `alarm_rt_state.py:272` duplicate `toggle_auto_refresh` (5 min, correctness bug).
- Convert `hyperparameters`/`pipeline_config` ORM columns to `JSONB` to delete the `isinstance(..., str)` branches (§6.6).
- Cache `communication_state.heatmap_matrix` and `model_performance_state.algorithm_comparison_data` (`@rx.var` → field).
