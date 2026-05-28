# Spec 03 — Database Schema & Background Process Catalog

**Generated:** 2026-05-28  
**Source scan:** migrations/*.sql · ksys_app/models/*.py · ksys_app/db.py · ksys_app/db_orm.py · ksys_app/schedulers/*.py · ksys_app/monitoring/*.py · ksys_app/utils/db_events.py · 20251030-rpi-pgcron/

---

## 1. Quick Count Summary

| Category | Count |
|---|---|
| **Tables (from migrations + ORM)** | 17 |
| **Hypertables (TimescaleDB)** | 4 |
| **Continuous Aggregates** | 5 |
| **Materialized Views** | 1 |
| **Regular Views** | 9 |
| **DB Functions / Stored Procs** | 12 |
| **DB Triggers** | 3 |
| **pg_cron Jobs** | 1 (+ optional cleanup) |
| **Python Schedulers** | 6 |
| **Monitoring classes** | 4 |

---

## 2. Table Catalog

### 2.1 Core Time-Series Tables (Hypertables)

#### `influx_hist` — Primary sensor data store (HYPERTABLE)
> The most important table in the system. All ingested sensor readings land here.

| Column | Type | Notes |
|---|---|---|
| ts | TIMESTAMPTZ | Partition key (hypertable time dim) |
| tag_name | VARCHAR(50) | Sensor identifier |
| value | FLOAT | Measured value |
| quality | INTEGER | 0=Good, 192=OK-legacy |

**Indexes:** `idx_tag_ts (tag_name, ts)`  
**Chunk interval:** Not explicitly set (TimescaleDB default = 7 days)  
**Write frequency:** Every sensor polling cycle (upstream data-injector container). Highest write volume table.  
**Also written by:** `calculate_virtual_tags()` pg_cron function (every 1 min), `ForecastScheduler` indirectly via virtual tags

---

#### `virtual_tag_values` — Calculated virtual sensor values (HYPERTABLE)

| Column | Type | Notes |
|---|---|---|
| time | TIMESTAMPTZ | Partition key |
| virtual_tag_id | VARCHAR(100) | FK → virtual_tags |
| value | DOUBLE PRECISION | Calculated result |
| quality_code | INTEGER | 0=Good, 1=Uncertain, 2=Bad, 3=Error |
| calculation_time_ms | INTEGER | Calculation latency |
| error_message | TEXT | Error if quality_code > 0 |

**Indexes:** `(virtual_tag_id, time DESC)`, `(quality_code, time DESC)`  
**Write frequency:** Every 1 minute via `batch_update_virtual_tags()` or VirtualTagScheduler  
**Trigger:** `trigger_sync_virtual_to_influx` → copies values to `influx_hist` on INSERT

---

#### `predictions` — Online forecast predictions (HYPERTABLE)

| Column | Type | Notes |
|---|---|---|
| target_time | TIMESTAMPTZ | PK part 1 — future time being predicted |
| tag_name | VARCHAR(50) | PK part 2 — FK → influx_tag |
| model_id | INTEGER | PK part 3 — FK → model_registry |
| horizon_minutes | INTEGER | PK part 4 |
| prediction_id | BIGSERIAL | Sequence ID |
| forecast_time | TIMESTAMPTZ | When prediction was generated |
| predicted_value | NUMERIC(15,4) | |
| ci_lower | NUMERIC(15,4) | 95% CI lower |
| ci_upper | NUMERIC(15,4) | 95% CI upper |
| actual_value | NUMERIC(15,4) | NULL until target_time passes |
| prediction_error | NUMERIC(15,4) | Filled by ActualValueUpdater |
| absolute_percentage_error | NUMERIC(10,4) | MAPE component |
| created_at / updated_at | TIMESTAMPTZ | |

**Indexes:** `idx_predictions_forecast_time`, `idx_predictions_tag_name`, `idx_predictions_model_id`, `idx_predictions_horizon`, `idx_predictions_tag_horizon`  
**Write frequency:** Every 10 min (ForecastScheduler writes N_models × N_horizons rows); backfilled every 10 min by ActualValueUpdater

---

#### `prediction_performance` — Hourly ML accuracy metrics (HYPERTABLE)

| Column | Type | Notes |
|---|---|---|
| evaluation_time | TIMESTAMPTZ | PK part 1 |
| model_id | INTEGER | PK part 2 — FK → model_registry |
| horizon_minutes | INTEGER | PK part 3 |
| performance_id | BIGSERIAL | |
| tag_name | VARCHAR(50) | |
| eval_start_time / eval_end_time | TIMESTAMPTZ | Hour window |
| num_predictions | INTEGER | |
| mape / rmse / mae | NUMERIC(10,4) | |
| r2_score | NUMERIC(10,6) | |
| mean_error / median_error / std_error | NUMERIC(15,4) | |
| ci_coverage_rate / ci_width_avg | NUMERIC | |

**Write frequency:** Every 1 hour (PerformanceAggregator), midnight cleanup

---

### 2.2 Continuous Aggregates (TimescaleDB)

These are TimescaleDB continuous aggregates materialized from `influx_hist`. They are read-only views populated automatically by TimescaleDB background workers.

| Aggregate View | Bucket Size | Refresh Policy | Lookback for Refresh |
|---|---|---|---|
| `influx_agg_1m` | 1 minute | every 1 min | last 2 hours |
| `influx_agg_10m` | 10 minutes | every 10 min | last 2 hours |
| `influx_agg_1h` | 1 hour | every 1 hour | last 7 days |
| `influx_agg_1d` | 1 day | every 1 day | last 30 days |
| `predictions_hourly` | 1 hour | every 1 hour | last 7 days |

**All aggregates expose:** `bucket, tag_name, n, avg, sum, min, max, last, first, diff`  
**Source SQL:** `migrations/09_setup_continuous_aggregate_refresh.sql`

---

### 2.3 Metadata / Config Tables

#### `influx_tag` — Sensor tag registry

| Column | Type | Notes |
|---|---|---|
| key | VARCHAR (PK) | Unique row key |
| tag_id | VARCHAR | Tag identifier |
| tag_name | VARCHAR (UNIQUE) | Human-readable name |
| tag_type | VARCHAR | 'sensor' or 'virtual' |
| meta | JSONB | Extra metadata |
| updated_at | TIMESTAMPTZ | |

**ORM class:** `SensorTag` (`sensor_orm.py`)  
**Also:** Virtual tags are registered here by `VirtualTagScheduler`

---

#### `influx_latest` — Latest sensor reading per tag (VIEW in migration 010)

After migration `010_viewer_tag.sql`, this is a **view** (not a plain table):

```sql
SELECT DISTINCT ON (h.tag_name) h.tag_name, h.ts, h.value, h.quality
FROM influx_hist h
INNER JOIN viewer_tag v ON h.tag_name = v.tag_name AND v.show_dashboard = true
WHERE h.ts > (now() - '1 day'::interval)
ORDER BY h.tag_name, h.ts DESC
```

**ORM class:** `SensorLatest` (maps to this view as if it were a table)

---

#### `influx_qc_rule` — QC/alarm threshold rules

| Column | Type | Notes |
|---|---|---|
| tag_name | VARCHAR(50) PK | |
| min_val / max_val | FLOAT | Normal operation range |
| warning_low / warning_high | FLOAT | Level 3 WARNING thresholds |
| critical_low / critical_high | FLOAT | Level 5 CRITICAL thresholds |

**ORM class:** `SensorQCRule`  
**Read by:** AlarmMonitor every 10 seconds (loads rules on init)

---

#### `virtual_tags` — Virtual tag definition / config

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| virtual_tag_id | VARCHAR(100) UNIQUE | |
| name / description | VARCHAR/TEXT | |
| unit | VARCHAR(20) | |
| calculation_type | VARCHAR(50) | 'expression' / 'statistical' / 'conditional' |
| config | JSONB | Formula, variables, thresholds |
| update_frequency | INTERVAL | Default 10 seconds |
| enabled | BOOLEAN | |
| created_at / updated_at | TIMESTAMPTZ | |

**Indexes:** `idx_virtual_tags_enabled`, `idx_virtual_tags_type`, GIN on `config`  
**Trigger:** `trigger_virtual_tag_update` → updates `updated_at` on UPDATE

---

#### `virtual_tag_definitions` — Alternative virtual tag config table (pg_cron version)

Used by the pg_cron-based `calculate_virtual_tags()` function (migration 07/08). Slightly different schema from `virtual_tags`:

| Column | Notes |
|---|---|
| tag_name | PK |
| formula_type | 'arithmetic' / 'conditional' / 'aggregation' |
| formula | Expression string |
| source_tags | TEXT[] |
| aggregation_function / aggregation_window | For aggregation type |
| condition / true_value / false_value | For conditional type |
| is_active | BOOLEAN |
| unit | VARCHAR |

**Hardcoded virtual tags in migration 08:** `PRESSURE_DIFF`, `RECOVERY_RATE`, `OPERATING_TIME`, `TOTAL_PRODUCT_VOLUME_1H`

---

#### `virtual_tag_dependencies` — Virtual tag → source sensor mapping

| Column | Type |
|---|---|
| id | SERIAL PK |
| virtual_tag_id | VARCHAR(100) FK → virtual_tags |
| source_tag_name | VARCHAR(100) |
| dependency_type | 'expression' / 'statistical' / 'conditional' |

**Unique constraint:** `(virtual_tag_id, source_tag_name)`

---

#### `viewer_tag` — Per-tag screen visibility control (migration 010)

| Column | Type | Notes |
|---|---|---|
| tag_name | TEXT PK | |
| display_order | INT | Sort order in UI |
| show_dashboard | BOOLEAN | Controls `influx_latest` view |
| show_alarm | BOOLEAN | Controls `influx_latest_alarm` |
| show_trend | BOOLEAN | Controls `influx_latest_trend` |
| show_model | BOOLEAN | Controls `influx_latest_model` |
| created_at / updated_at | TIMESTAMPTZ | |

**Trigger:** `viewer_tag_updated_at` → updates `updated_at`

---

#### `model_registry` — ML model metadata + pickle storage

| Column | Type | Notes |
|---|---|---|
| model_id | INTEGER PK | |
| model_name / model_type / version | VARCHAR | e.g., 'AUTO_ARIMA', 'PROPHET', 'XGBOOST' |
| tag_name | VARCHAR(50) | Sensor this model predicts |
| hyperparameters / feature_config / pipeline_config | JSONB | Training config |
| model_pickle | BYTEA | Serialized model object (primary) |
| model_path | TEXT | Legacy file path (fallback) |
| model_size_bytes | BIGINT | |
| training_data_start / end / samples / duration_seconds | Various | |
| train_mape / train_rmse / train_mae | NUMERIC(10,4) | Training metrics |
| validation_mape / validation_rmse / validation_mae | NUMERIC(10,4) | |
| is_active / is_deployed | BOOLEAN | `is_deployed=TRUE` → triggers forecast |
| deployed_at / deployed_by | TIMESTAMPTZ / VARCHAR | |
| created_at / created_by | TIMESTAMPTZ / VARCHAR | |

**Unique:** `(tag_name, model_type, version)`  
**Indexes:** `idx_model_registry_tag_name`, `idx_model_registry_model_type`, `idx_model_registry_active`  
**ORM class:** `ModelRegistry` (`forecasting_orm.py`)

---

#### `training_evaluation` — Offline backtest results

| Column | Type | Notes |
|---|---|---|
| evaluation_id | BIGSERIAL PK | |
| model_id | INTEGER FK → model_registry | |
| evaluation_time | TIMESTAMPTZ | When model was trained |
| target_time | TIMESTAMPTZ | Test set timestamp (PAST) |
| predicted_value / actual_value | NUMERIC(15,4) | |
| prediction_error / absolute_percentage_error | NUMERIC | |
| horizon_minutes | INTEGER | 60/120/360/720/1440 |
| model_type / sensor_tag | VARCHAR | |

**Unique:** `(model_id, target_time, horizon_minutes)`  
**Written by:** Training Wizard + ActualValueUpdater (backfills `actual_value`)

---

#### `forecast_player_cache` — Pre-computed UI cache

| Column | Type | Notes |
|---|---|---|
| cache_id | SERIAL PK | |
| model_id / tag_name | INT / VARCHAR | |
| forecast_time / reference_time / created_at | TIMESTAMPTZ | |
| rolling_window | JSONB | Array: Past 30 + Present 1 + Future N |
| predictions_data | JSONB | 7-row table display data |
| mape / rmse / mae / accuracy | NUMERIC(10,2) | |
| next_forecast_at | TIMESTAMPTZ | |
| latest_value | NUMERIC(10,2) | |

**Unique:** `(model_id, forecast_time)`  
**Write frequency:** Every 10 min (ForecastScheduler after save_predictions)  
**Read by:** Forecast Player UI page (single SELECT, target <50ms)

---

#### `feature_store` — Engineered ML features (HYPERTABLE candidate)

| Column | Type | Notes |
|---|---|---|
| feature_time | TIMESTAMPTZ PK | |
| tag_name | VARCHAR(50) PK | |
| feature_id | BIGSERIAL | |
| lag_1h / lag_3h / lag_6h / lag_12h / lag_24h | NUMERIC(15,4) | |
| rolling_mean/std/min/max_6h | NUMERIC | 6-hour window stats |
| rolling_mean/std/min/max_24h | NUMERIC | 24-hour window stats |
| rolling_mean/std_1w | NUMERIC | 1-week stats |
| hour_of_day / day_of_week / month / quarter / is_weekend / is_business_hour | INT/BOOL | Calendar features |
| trend/seasonal/residual_component | NUMERIC | STL decomposition |
| rate_of_change / acceleration | NUMERIC | |

**ORM class:** `FeatureStore`

---

#### `drift_monitoring` — Model/data drift records (HYPERTABLE candidate)

| Column | Type | Notes |
|---|---|---|
| monitoring_time | TIMESTAMPTZ PK | |
| tag_name | VARCHAR(50) PK | |
| drift_type | VARCHAR(50) PK | |
| model_id | INTEGER optional FK | |
| psi_score / ks_statistic / ks_pvalue / js_divergence | NUMERIC | Statistical tests |
| current_mean/std/min/max | NUMERIC | Current window stats |
| reference_mean/std/min/max | NUMERIC | Reference window stats |
| is_drift_detected | BOOLEAN | |
| drift_severity | VARCHAR(20) | low/medium/high/critical |
| current/reference window start/end | TIMESTAMPTZ | |
| action_taken / alert_sent | VARCHAR / BOOLEAN | |

**ORM class:** `DriftMonitoring`

---

#### `alarm_history` — Alarm event log

| Column | Type | Notes |
|---|---|---|
| event_id | VARCHAR(50) PK | e.g., `ALM-20251002120000-TMP` |
| scenario_id | VARCHAR(20) | e.g., `TMP__CRIT` |
| level | INTEGER | 1=INFO, 2=NOTICE, 3=WARN, 4=CRIT, 5=EMRG |
| triggered_at | TIMESTAMPTZ | |
| message | TEXT | Human-readable alarm text |
| sensor_data | JSONB | `{tag_name, value, timestamp}` |
| actions_taken | TEXT[] | e.g., `["알람 생성", "모니터링"]` |
| acknowledged | BOOLEAN | Default false |
| acknowledged_by / acknowledged_at | VARCHAR / TIMESTAMPTZ | |
| resolved | BOOLEAN | Default false |
| resolved_at | TIMESTAMPTZ | |

**Indexes (migration 001):**
- `idx_alarm_triggered_at (triggered_at DESC)`
- `idx_alarm_level_acknowledged (level DESC, acknowledged) WHERE resolved=false`
- `idx_alarm_sensor_tag ((sensor_data->>'tag_name'))`
- `idx_alarm_scenario_triggered (scenario_id, triggered_at DESC) WHERE resolved=false`
- `idx_alarm_unacknowledged (acknowledged, triggered_at DESC) WHERE acknowledged=false AND resolved=false`

**Write frequency:** On threshold violation during AlarmMonitor 10-second check cycle

---

#### `tag_value_history` — Tag value change log (created by DataLogger)

| Column | Type |
|---|---|
| id | BIGSERIAL PK |
| tag_name | VARCHAR(100) |
| old_value / new_value | DOUBLE PRECISION |
| delta_value | DOUBLE PRECISION |
| timestamp / created_at | TIMESTAMPTZ |

---

#### `kpi_state_history` — KPI status transition log (created by DataLogger)

| Column | Type |
|---|---|
| id | BIGSERIAL PK |
| tag_name | VARCHAR(100) |
| old_status / new_status | VARCHAR(20) |
| gauge_percent / qc_min / qc_max / current_value | DOUBLE PRECISION |
| timestamp / created_at / reason | TIMESTAMPTZ / VARCHAR |

---

### 2.4 Views Created by Migrations

| View Name | Purpose | Filter |
|---|---|---|
| `influx_latest` | Latest value per tag | `show_dashboard=true`, last 1 day |
| `influx_latest_dashboard` | Dashboard screen | `show_dashboard=true` |
| `influx_latest_alarm` | Alarm screen | `show_alarm=true` |
| `influx_latest_trend` | Trend screen | `show_trend=true` |
| `influx_latest_model` | Model training candidates | `show_model=true` |
| `virtual_tags_as_influx` | Virtual tags in influx format | `value IS NOT NULL` |
| `influx_latest_with_virtual` | Sensors + virtual tags combined | |
| `all_tags_info` | influx_tag + virtual_tags union | |
| `influx_hist_with_virtual` | influx_hist + virtual_tag_values union | |

**Materialized view:** `virtual_tag_latest` — latest value per virtual_tag_id (refreshed by `batch_update_virtual_tags()`)

---

## 3. DB Connection Architecture

### 3.1 `db.py` — asyncpg direct pool (primary)

```
_GLOBAL_POOL (asyncpg.Pool)
  min_size = 1
  max_size = 10
  timeout = 60s
  command_timeout = 60s
```

**Usage pattern:** `q(sql, params)` → `pool.acquire()` → `conn.fetch()` → returns `list[dict]`  
**Fallback:** On timeout, opens a direct `asyncpg.connect()` without pool  
**Used by:** `DashboardModel`, `AlarmMonitor`, `DataLogger`, `DatabaseEventListener` (db_events.py)

### 3.2 `db_orm.py` — SQLAlchemy async + asyncpg (secondary)

```
EngineManager (lazy singleton)
  USE_DB_POOLING env (default: false → NullPool)
  NullPool: Fresh connection per get_async_session() call (Reflex BG event compatible)
  AsyncAdaptedQueuePool (opt-in): pool_size=10, max_overflow=10, pool_timeout=30, pool_recycle=1800
  command_timeout = 30s (env: DB_COMMAND_TIMEOUT)
  statement_timeout = 30000ms server-side (env: DB_STATEMENT_TIMEOUT_MS)
  connect_timeout = 10s
  application_name = "reflex_app"
  jit = off
```

**Usage pattern:** `async with get_async_session() as session:` → SQLAlchemy `session.execute(text(...))` or ORM select  
**Used by:** All forecasting schedulers (ForecastScheduler, ActualValueUpdater, PerformanceAggregator), VirtualTagScheduler

---

## 4. Migration Execution Order

| Order | File | Content |
|---|---|---|
| 1 | `01_init_virtual_tags.sql` | Creates virtual_tags, virtual_tag_values (hypertable), virtual_tag_dependencies, virtual_tag_latest |
| 2 | `02_functions_virtual_tags.sql` | DB functions: parse_expression, calculate_statistical_tag, calculate_virtual_tag, batch_update_virtual_tags |
| 3 | `03_sample_virtual_tags.sql` | 8 sample virtual tag INSERT rows |
| 4 | `04_add_virtual_tag.sql` | COOLING_EFFICIENCY, SYSTEM_LOAD_PCT INSERTs |
| 5 | `05_modify_virtual_tag.sql` | UPDATE examples for existing virtual tags |
| 6 | `06_integrate_with_influx.sql` | Trigger: sync virtual tags → influx_hist; views: influx_latest_with_virtual etc. |
| 7 | `07_pg_cron_migration.sql` | Installs pg_cron; `calculate_virtual_tags()` function v1 (reads virtual_tag_definitions) |
| 8 | `08_pg_cron_virtual_tags.sql` | `calculate_virtual_tags()` function v2 (simplified, hardcoded 4 VTags); pg_cron schedule every 1 min |
| 9 | `09_setup_continuous_aggregate_refresh.sql` | Continuous aggregate policies for influx_agg_1m/10m/1h/1d + predictions_hourly |
| 10 | `010_viewer_tag.sql` | viewer_tag table; influx_latest redefined as view; 4 screen-specific views |
| 11 | `001_alarm_indexes.sql` | 5 partial indexes on alarm_history |
| 12 | `20251014_create_training_evaluation.sql` | training_evaluation table; v_latest_evaluation_metrics view; v_evaluation_timeseries view |
| 13 | `20251017_create_forecast_player_cache.sql` | forecast_player_cache table; cleanup function |

**Latest migration:** `20251017_create_forecast_player_cache.sql` (dated 2025-10-17)  
**Note:** `001_alarm_indexes.sql` uses lexicographic sort order before `01_init_virtual_tags.sql` — this is a file naming issue but all assume alarm_history already exists (created elsewhere, likely in a base init script not in the migrations folder).

---

## 5. Scheduler Inventory

### 5.1 `ForecastScheduler` — Online predictions

| Property | Value |
|---|---|
| File | `ksys_app/schedulers/forecast_scheduler.py` (~700+ LoC) |
| Interval | Every 10 minutes (x:00, x:10, x:20, ...) |
| Trigger type | `asyncio.sleep(600)` loop with initial alignment delay |
| Task | Generate predictions for all `is_deployed=TRUE` models |
| Reads | `model_registry` (deployed models), `influx_agg_10m` (latest sensor value at T0) |
| Writes | `predictions` (N_models × N_horizons rows), `forecast_player_cache` |
| Horizons | Default [60, 120, 360, 720, 1440] min OR overrides from `pipeline_config.forecast_config.horizons` |
| Per-model timeout | `FORECAST_MODEL_PREDICT_TIMEOUT` env (default 45s) |
| Pickle load timeout | `FORECAST_PICKLE_LOAD_TIMEOUT` env (default 15s) |
| ML execution | Runs in ThreadPoolExecutor + new event loop per model (async models) |
| Supported model types | AUTO_ARIMA (statsforecast), PROPHET, XGBOOST |

**Sensor selection logic:** Queries `model_registry WHERE is_deployed=TRUE AND is_active=TRUE`. No additional sensor filtering — one model = one tag.

**Forecast loop within `_process_model()`:**
1. Get horizons from `pipeline_config` (or use defaults)
2. `get_latest_sensor_value(tag_name, reference_time)` → queries `influx_agg_10m`, rounds to 10-min boundary
3. `load_model_from_bytea(model_pickle)` → `pickle.loads()` in executor thread with timeout
4. `generate_predictions(model, model_type, last_value, horizons)` → calls `model.predict(len(horizons))`
5. `save_predictions()` → INSERT N rows into `predictions`
6. `generate_forecast_player_cache()` → INSERT 1 row into `forecast_player_cache`

---

### 5.2 `ActualValueUpdater` — Backfill actuals

| Property | Value |
|---|---|
| File | `ksys_app/schedulers/actual_value_updater.py` |
| Interval | Every 10 minutes (x:01, x:11, x:21, ...) — 1 min after ForecastScheduler |
| Task | Fill `actual_value` in predictions + training_evaluation when target_time has passed |
| Reads | `predictions` (WHERE target_time <= NOW() AND actual_value IS NULL), `influx_hist` |
| Writes | `predictions.actual_value / prediction_error / absolute_percentage_error`, same fields in `training_evaluation` |
| Batch size | 100 records per iteration, up to 20 batches per run |
| Time range | Only looks back 7 days for predictions |
| Match tolerance | Joins influx_hist BETWEEN target_time ± 5 minutes |
| Statement timeout | 15s per batch |

---

### 5.3 `PerformanceAggregator` — Hourly accuracy metrics

| Property | Value |
|---|---|
| File | `ksys_app/schedulers/performance_aggregator.py` |
| Interval | Every 1 hour (x:03, x:13, x:23, ...) — aligns 3 min after ForecastScheduler |
| Task | Aggregate completed predictions into `prediction_performance` |
| Reads | `predictions WHERE actual_value IS NOT NULL AND forecast_time >= NOW()-1h` |
| Writes | `prediction_performance` (UPSERT), daily cleanup (midnight only) |
| Minimum data | Requires COUNT >= 3 for any aggregation |
| Retention | Keeps 90 days; deletes older records at hour=0 |

---

### 5.4 `VirtualTagScheduler` — Calculate virtual tags

| Property | Value |
|---|---|
| File | `ksys_app/schedulers/virtual_tag_scheduler.py` |
| Interval | Every 1 minute (`asyncio.sleep(60)`) |
| Task | Calculate all active virtual tags via `VirtualTagService`; register them in `influx_tag` |
| Reads | `virtual_tag_definitions` (active tags), `influx_latest` (source sensor values) |
| Writes | `influx_hist` (via trigger on virtual_tag_values), `influx_tag` (upsert on first run) |
| Note | Partially superseded by pg_cron `calculate_virtual_tags()` — both may run |

---

### 5.5 `AlarmScheduler` (psycopg2-based, legacy)

| Property | Value |
|---|---|
| File | `ksys_app/monitoring/alarm_scheduler.py` |
| Interval | Every 60 seconds (threading.Thread loop) |
| Task | Calls DB function `manual_alarm_schedule()`; reads `alarm_schedule_log` for stats |
| Uses | `psycopg2` (synchronous, runs in a background thread) |
| Note | Legacy sync scheduler, separate from the async AlarmMonitor |

---

### 5.6 `DailyTrainingScheduler` — Retrain ML models

| Property | Value |
|---|---|
| File | `ksys_app/schedulers/daily_training.py` |
| Interval | Daily at 2 AM (not yet activated in scheduler_manager) |
| Task | Collect 30 days data → train models → evaluate → deploy if better → drift check |
| Reads | `influx_hist` (30 days), `model_registry` |
| Writes | `model_registry` (new model rows + pickle), drift alerts |
| Status | Code exists; not wired into `scheduler_manager.py` start_all() |

---

### 5.7 pg_cron Job — `calculate_virtual_tags_every_minute`

| Property | Value |
|---|---|
| Host | Inside PostgreSQL container (pgai-db) |
| Schedule | `* * * * *` — every 1 minute |
| Command | `SELECT calculate_virtual_tags()` |
| Reads | `influx_latest` (for source sensor values) |
| Writes | `influx_hist` (UPSERT ON CONFLICT (ts, tag_name)) |
| Virtual tags | PRESSURE_DIFF, RECOVERY_RATE, OPERATING_TIME, TOTAL_PRODUCT_VOLUME_1H |
| Container | `rpi-finished-pgai-db` — built from `20251030-rpi-pgcron/Dockerfile.rpi-pgcron` |
| Base image | `timescale/timescaledb:latest-pg17` (Alpine) |
| Extensions | TimescaleDB + pg_cron (shared_preload_libraries=timescaledb,pg_cron) |

---

## 6. Monitoring Inventory

### 6.1 `AlarmMonitor` / `AlarmMonitorFixed`

| Property | Value |
|---|---|
| File | `monitoring/alarm_monitor.py` (original), `monitoring/alarm_monitor_fixed.py` (ISA-18.2 compliant) |
| Poll interval | Every **10 seconds** (`check_interval = 10`) |
| Reads | `influx_hist WHERE ts >= NOW()-1min` (latest values) |
| Alarm rules | `influx_qc_rule` — loaded on init; 3 levels: normal / warning / critical |
| Dedup window | 5 minutes — if same (tag_name, level) alarm exists in last 5 min, skip |
| Writes | `alarm_history` INSERT |
| NOTIFY | `pg_notify('alarm_event', event_id)` after INSERT |
| Level mapping | 2=NOTICE, 3=WARN, 4=CRIT |
| Scenario ID | `{tag_prefix}_{INFO/NOTICE/WARN/CRIT/EMRG}` |

**Fixed vs original:** `alarm_monitor_fixed.py` reads `warning_low/warning_high/critical_low/critical_high` columns and adds ISA-18.2 compliance label; original uses `warn_min/warn_max/alarm_min/alarm_max` columns.

---

### 6.2 `DatabaseEventListener` (db_events.py)

| Property | Value |
|---|---|
| File | `ksys_app/utils/db_events.py` |
| Protocol | PostgreSQL LISTEN/NOTIFY (psycopg 3 async) |
| Default channel | `"data_update"` (configurable) |
| Connection | Dedicated connection (not from pool) with `autocommit=True` |
| Listen timeout | 5 seconds per `notifies()` cycle |
| Callback | Parses JSON payload → calls registered async callback |
| Producer | `alarm_monitor.py` sends `NOTIFY alarm_event, '<event_id>'` |
| Also supports | `notify(payload)` method — sends NOTIFY from a fresh connection |

**NOTIFY/LISTEN event flow:**
```
AlarmMonitor.create_alarm_event()
  → INSERT INTO alarm_history
  → SELECT pg_notify('alarm_event', event_id)
  → [DB sends NOTIFY]
  → DatabaseEventListener._listen_loop()
  → JSON parse
  → callback(payload)
  → [Frontend state update]
```

---

### 6.3 `DataLogger`

| Property | Value |
|---|---|
| File | `monitoring/data_logger.py` |
| Purpose | Log value changes and KPI state transitions |
| Pool | Own asyncpg pool: min=2, max=10, command_timeout=10 |
| Writes | `tag_value_history`, `kpi_state_history`, `alarm_history` |
| Tables created on init | If not exist: `tag_value_history`, `kpi_state_history`, `alarm_history` |
| Trigger | Significant delta change or KPI state transition |

---

### 6.4 `RangeMonitor`

| Property | Value |
|---|---|
| File | `monitoring/range_monitor.py` |
| Purpose | Desalination plant operational range monitoring |
| Thresholds | Hardcoded in `_initialize_thresholds()` for TMP (막간차압), DP (차압), and others |
| Alert levels | NORMAL / WARNING / CRITICAL / EMERGENCY (enum) |
| Features | Predicts time-to-critical based on trend data |
| Integration | Uses psycopg3 directly |

---

## 7. ORM Class ↔ Table Mapping

| ORM Class | File | Table | Notes |
|---|---|---|---|
| `SensorTag` | sensor_orm.py | `influx_tag` | |
| `SensorLatest` | sensor_orm.py | `influx_latest` (view after 010) | PK = tag_name |
| `SensorQCRule` | sensor_orm.py | `influx_qc_rule` | |
| `SensorHistory` | sensor_orm.py | `influx_hist` | |
| `SensorAggregation` | sensor_orm.py | `influx_agg_1h` (view) | |
| `ModelRegistry` | forecasting_orm.py | `model_registry` | |
| `Prediction` | forecasting_orm.py | `predictions` | Hypertable |
| `PredictionPerformance` | forecasting_orm.py | `prediction_performance` | Hypertable |
| `FeatureStore` | forecasting_orm.py | `feature_store` | |
| `DriftMonitoring` | forecasting_orm.py | `drift_monitoring` | |
| `TimeseriesRow` | models.py | `influx_agg_*` views (Pydantic DTO) | |
| `Feature5mRow` | models.py | — (Pydantic DTO for 5m feature query) | |
| `LatestRow` | models.py | `influx_latest` (Pydantic DTO) | |
| `Indicator1mRow` | models.py | — (Pydantic DTO, technical indicators) | |
| `DashboardModel` | dashboard.py | Queries `influx_latest`, `influx_qc_rule`, `influx_agg_1h` | Pure SQL, not ORM |

---

## 8. Critical Data Flow Diagrams

### 8.1 Sensor Data Ingestion Flow

```
[Upstream IoT / Cloud DB]
        |
        | (periodic sync — sync_monitor_state or data-injector container)
        v
[data-injector container OR pg_cron job]
        |
        | INSERT INTO influx_hist (ts, tag_name, value, quality)
        v
+------------------+
|   influx_hist    |  <-- PRIMARY data store (TimescaleDB hypertable)
|   (hypertable)   |
+------------------+
        |
        |---> TimescaleDB background: influx_agg_1m/10m/1h/1d (continuous aggregates refresh)
        |
        |---> trigger_sync_virtual_to_influx: when virtual_tag_values INSERT
        |       → virtual_tag_values ALSO writes back to influx_hist
        |
        |---> influx_latest (VIEW, derived from influx_hist + viewer_tag)
        |
        v
[All pages query influx_hist / influx_latest / influx_agg_* ]
```

---

### 8.2 Forecast Loop (10-minute cycle)

```
x:00 — ForecastScheduler.run_once()
  |
  |-- SELECT model_registry WHERE is_deployed=TRUE
  |       ↓
  |-- For each model (concurrent with per-model timeout 45s):
  |       ↓
  |   GET influx_agg_10m[tag_name, T0=round(now,10m)]  → last_value
  |       ↓
  |   pickle.loads(model_registry.model_pickle)  → model object
  |       ↓ (run in ThreadPoolExecutor)
  |   model.predict(N_horizons)  → forecast_df [pandas DataFrame]
  |       ↓
  |   INSERT N rows → predictions (target_time = T0 + horizon_i)
  |       ↓
  |   INSERT 1 row → forecast_player_cache (rolling_window JSON, metrics)
  |
x:01 — ActualValueUpdater.run_once()
  |
  |-- SELECT predictions WHERE target_time <= NOW() AND actual_value IS NULL
  |-- JOIN influx_hist ON tag_name WHERE ts BETWEEN target ± 5min
  |-- UPDATE predictions SET actual_value, prediction_error, APE
  |-- UPDATE training_evaluation SET actual_value (same logic)
  |
x:03 — PerformanceAggregator.run_once() (actually runs hourly at x:03)
  |
  |-- INSERT INTO prediction_performance
  |       SELECT model_id, horizon_minutes, MAE/MAPE/RMSE
  |       FROM predictions WHERE actual_value IS NOT NULL AND last 1 hour
  |-- midnight: DELETE prediction_performance WHERE older than 90 days
```

---

### 8.3 Alarm Loop (10-second cycle)

```
AlarmMonitor (continuous loop, sleep=10s)
  |
  |-- SELECT DISTINCT ON (tag_name) FROM influx_hist WHERE ts >= NOW()-1min
  |       ↓
  |-- For each row: evaluate against influx_qc_rule thresholds
  |       ↓
  |   [Normal / Warning / Critical check]
  |       ↓ (if threshold exceeded AND no duplicate alarm in last 5 min)
  |   INSERT INTO alarm_history (event_id, scenario_id, level, sensor_data…)
  |       ↓
  |   SELECT pg_notify('alarm_event', event_id)
  |       ↓
  |
DatabaseEventListener (dedicated psycopg3 LISTEN connection)
  |
  |-- LISTEN alarm_event
  |-- On NOTIFY: parse JSON → callback(payload)
  |-- callback → Reflex state update → WebSocket push → frontend UI refresh
```

---

## 9. DB Read/Write Hotspot Analysis

| Table | Write Frequency | Primary Writers |
|---|---|---|
| `influx_hist` | Continuous (every ~10s from data-injector) | data-injector, virtual_tag trigger, pg_cron |
| `predictions` | Every 10 min × N_models × N_horizons | ForecastScheduler |
| `forecast_player_cache` | Every 10 min × N_models | ForecastScheduler |
| `predictions.actual_value` | Every 10 min (batch 100) | ActualValueUpdater |
| `alarm_history` | On threshold violation (every 10s check) | AlarmMonitor |
| `virtual_tag_values` | Every 1 min | VirtualTagScheduler |
| `prediction_performance` | Every 1 hour | PerformanceAggregator |
| `model_registry.model_pickle` | On training completion (daily or on-demand) | DailyTrainingScheduler |

**Top read tables:**
1. `influx_hist` — polled by AlarmMonitor (10s), ActualValueUpdater (10m), query pages
2. `influx_latest` (view) — polled by Dashboard page, DashboardModel
3. `influx_agg_10m` — polled by ForecastScheduler every 10 min
4. `influx_agg_1h` / `influx_agg_1d` — polled by Trend page
5. `forecast_player_cache` — read by Forecast Player UI (single SELECT per render)

---

## 10. Scheduler Coordination Summary

```
SchedulerManager.start_all()  [called once on app startup via asyncio.create_task]
  |
  |-- ForecastScheduler.start(600s) ──────── starts at x:00 boundary
  |-- ActualValueUpdater.start(600s) ──────── starts at x:01 boundary
  |-- PerformanceAggregator.start(3600s) ─── starts at x:03 boundary
  |
  |-- [DailyTrainingScheduler NOT wired here — separate activation needed]
  |-- [VirtualTagScheduler NOT in SchedulerManager — separate asyncio task]
  |-- [AlarmScheduler runs as threading.Thread — separate lifecycle]
  |-- [pg_cron runs inside PostgreSQL — independent of Python process]
```

**Container architecture note:** The pg_cron DB container (`rpi-finished-pgai-db`) is built from `20251030-rpi-pgcron/Dockerfile.rpi-pgcron` which installs pg_cron on top of `timescale/timescaledb:latest-pg17` (Alpine). The Python schedulers run inside the app container (`rpi-finished-reflex-app`). They share the same PostgreSQL database.

---

*End of spec_03_database_schedulers.md*
