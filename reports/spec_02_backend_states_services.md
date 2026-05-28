# Backend State/Service Layer Catalog — KSYS App
> Generated: 2026-05-28 | Source: ksys_app/states/, ksys_app/services/, ksys_app/ai_engine/, ksys_app/controllers/
> Companion to: `reports/spec_01_frontend_pages.md`

---

## TL;DR — Surface Area Summary

| Metric | Count |
|--------|------:|
| State classes (total)                              | 24 |
| State classes used by registered pages             | 12 |
| Orphaned state classes (defined, no page reference) | 7  |
| `@rx.event` handlers (all)                         | 201 |
| `@rx.event(background=True)` handlers              | 112 |
| `@rx.var` computed properties                      | 268 |
| Service classes (`services/`)                      | 11 |
| AI engine modules (`ai_engine/`)                   | 18 |
| Controllers (`controllers/`)                       | 1 (dashboard_controller.py — DB connection wrapper only) |

**Top 5 pages by backend surface (event handlers + vars):**

1. `/training-wizard` — TrainingWizardState (extends TrainingState) — 17 events + 50+ vars
2. `/forecast` — ForecastPlayerState — 22 events + 57 vars
3. `/` (Dashboard) — DashboardState (1635 LOC) + DashboardRealtimeState — 44 events + 30 vars combined
4. `/trend` — TrendState — 17 events + 16 vars
5. `/alarms` — AlarmsState — 17 events + 19 vars

---

## State Class Master Table

| State Class | File | Parent | Vars (approx) | @rx.event | bg events | @rx.var | Used by page? |
|-------------|------|--------|--------------:|----------:|----------:|--------:|---------------|
| `BaseState`                  | states/base_state.py                          | rx.State                | 5 | 5 | 3 | 0 | (mixin only) |
| `DashboardRealtimeState`     | states/dashboard_realtime.py                  | BaseState               | 28 | 4 | 4 | 10 | `/` |
| `DashboardState`             | states/dashboard/state.py                     | rx.State                | 50+ | 40 | 4 | 18 | (legacy components only — features_table, indicators_table) |
| `AlarmsState`                | states/alarms.py                              | rx.State                | 26 | 17 | 12 | 19 | `/alarms` |
| `AlarmRTState`               | states/alarm_rt_state.py                      | rx.State                | 21 | 7 | 7 | 0 | `/alarms_rt`, `/alarms_rt_new` |
| `AlarmHistState`             | states/alarm_hist_state.py                    | rx.State                | 22 | 9 | 3 | 0 | `/alarms_hist`, `/alarms_hist_new` |
| `AlarmState`                 | states/alarm_state.py                         | rx.State                | 15 | 10 | 5 | 0 | ORPHAN (referenced only as docstring in stat_card.py) |
| `AlarmsEnhancedState`        | states/alarms_enhanced.py                     | TagHierarchyState       | ~25 | 5 | 3 | 8 | ORPHAN (not imported by any page) |
| `ScadaAlarmState`            | states/scada_alarm_state.py                   | rx.State                | ~12 | 0 (only `def`) | 0 | 0 | `/scada-alarms` |
| `ScadaAlarmComparisonState`  | states/scada_alarm_comparison_state.py        | rx.State                | ~10 | 0 (only `def`) | 0 | 0 | `/scada-alarm-comparison` |
| `CommunicationState`         | states/communication_state.py                 | rx.State                | 8 | 4 | 4 | 15 | `/comm` |
| `TrendState`                 | states/trend_state.py                         | rx.State                | ~30 | 17 | 7 | 16 | `/trend` (alias `T`) |
| `TrendStateEnhanced`         | states/trend_state_enhanced.py                | TagHierarchyState       | ~30 | 18 | 8 | 17 | ORPHAN (not imported by any page) |
| `TrainingState`              | states/training_state/state.py                | rx.State                | ~40 | 7 | 7 | 5 | (used as base for TrainingWizardState only) |
| `TrainingWizardState`        | states/training_wizard_state.py               | TrainingState           | ~10 + inherited | 2 | 2 | 37 | `/training-wizard` |
| `TrainingWizardStateEnhanced`| states/training_wizard_state_enhanced.py      | TrainingWizardState, TagHierarchyState | ~5 | 6 | 1 | 5 | ORPHAN (not imported by any page) |
| `ForecastPlayerState`        | states/forecast_player_state/state.py         | BaseState               | ~40 | 9 | 9 | 57 | `/forecast` (alias `FPS`) |
| `ModelPerformanceState`      | states/model_performance_state.py             | rx.State                | ~25 | 11 | 6 | 16 | `/model-performance` (alias `M`) |
| `ModelConfigState`           | states/model_config_state.py                  | rx.State                | ~15 | 6 | 6 | 0 | ORPHAN (not imported by any page) |
| `ViewerTagState`             | states/viewer_tag_state.py                    | rx.State                | ~10 | 10 | 10 | 0 | `/viewer-tag` |
| `AIState`                    | states/ai_state.py                            | rx.State                | ~10 | 7 | 4 | 32 | `/ai` (UNREGISTERED page — frontend orphan) |
| `SchedulerState`             | states/scheduler_state.py                     | rx.State                | ~5 | 1 | 1 | 0 | (loaded from `ksys_app.py`, no page UI) |
| `SyncMonitorState`           | states/sync_monitor_state.py                  | rx.State                | ~10 | 4 | 4 | 0 | ORPHAN |
| `TagHierarchyState`          | states/tag_hierarchy_state.py                 | BaseState               | ~10 | 1 | 1 | 6 | (mixin for Enhanced* states) |
| `DashboardRealtimeGroupedState` | states/dashboard_realtime_grouped.py       | TagHierarchyState       | ~15 | 1 | 1 | 7 | ORPHAN (not imported by any page) |

**Orphan list (defined but no page uses them):**
1. `AlarmState` (states/alarm_state.py) — legacy AI/rule unified alarm state, superseded by `AlarmsState`
2. `AlarmsEnhancedState` (states/alarms_enhanced.py) — TagHierarchy-aware version of AlarmsState
3. `TrendStateEnhanced` (states/trend_state_enhanced.py) — TagHierarchy-aware Trend state
4. `TrainingWizardStateEnhanced` (states/training_wizard_state_enhanced.py)
5. `DashboardRealtimeGroupedState` (states/dashboard_realtime_grouped.py)
6. `ModelConfigState` (states/model_config_state.py)
7. `SyncMonitorState` (states/sync_monitor_state.py)

The 5 `*Enhanced` / `*Grouped` orphans appear to be in-progress UX refactors. `ModelConfigState` and `SyncMonitorState` lack any page binding; treat as dead code unless a new page is planned.

---

## Cross-State Inheritance Graph

```
rx.State
  ├── BaseState (base_state.py)
  │     ├── DashboardRealtimeState
  │     ├── ForecastPlayerState
  │     └── TagHierarchyState
  │           ├── DashboardRealtimeGroupedState   [orphan]
  │           ├── AlarmsEnhancedState              [orphan]
  │           ├── TrendStateEnhanced               [orphan]
  │           └── TrainingWizardStateEnhanced (multi-inherits TrainingWizardState too) [orphan]
  │
  ├── TrainingState
  │     └── TrainingWizardState
  │           └── TrainingWizardStateEnhanced [orphan]
  │
  ├── AlarmsState
  ├── AlarmState (legacy)         [orphan]
  ├── AlarmRTState
  ├── AlarmHistState
  ├── AIState                     [orphan via page — page /ai not registered]
  ├── CommunicationState
  ├── ScadaAlarmState
  ├── ScadaAlarmComparisonState
  ├── TrendState
  ├── ModelConfigState            [orphan]
  ├── ModelPerformanceState
  ├── SchedulerState              (singleton, used in startup hook in ksys_app.py:204)
  ├── SyncMonitorState            [orphan]
  ├── DashboardState (states/dashboard/state.py — legacy giant)
  └── ViewerTagState
```

---

# Per-Domain Catalog

## Domain Mapping

| Domain | State files | Service files | ai_engine files | Key event handlers (test priority high) |
|--------|-------------|---------------|-----------------|-----------------------------------------|
| Alarm        | alarms.py, alarm_rt_state.py, alarm_hist_state.py, alarm_state.py [orphan], alarms_enhanced.py [orphan], scada_alarm_state.py, scada_alarm_comparison_state.py | alarm_service.py | (none) | `acknowledge_alarm`, `acknowledge_selected`, `set_severity_filter`, `cleanup_old_alarms` |
| Dashboard / Sensor | dashboard_realtime.py, dashboard/state.py, dashboard_realtime_grouped.py [orphan] | sensor_service.py | (none) | `save_sensor_info` (DB write), `start_streaming`, `_fetch_data` |
| Forecast / Prediction | forecast_player_state/state.py | forecast_service.py | (none) | `trigger_forecast_now`, `deploy_model`, `load_predictions`, `start_streaming` |
| Training (offline ML) | training_state/state.py, training_wizard_state.py, training_wizard_state_enhanced.py [orphan] | feature_config_service.py, feature_config_service_v2.py, feature_config_service_final.py, feature_engineering_service.py, model_config_service.py | (none) | `start_training`, `save_model`, `create_feature_config` |
| Communication | communication_state.py | communication_service.py | (none) | `load_data`, `refresh_data` |
| Trend          | trend_state.py, trend_state_enhanced.py [orphan] | trend_service.py | (none) | `load_series_data`, `export_csv_all`, `export_csv_page` |
| Model Performance / Deploy | model_performance_state.py, model_config_state.py [orphan] | model_config_service.py | (none) | `deploy_model`, `delete_model`, `undeploy_model` |
| AI / RAG       | ai_state.py | ai_service.py | rag_engine.py, rag_engine_pgvector.py, graph_rag_engine.py, dynamic_rag_engine.py, llamaindex_rag_engine.py, knowledge_*.py, pandas_analysis_engine.py, response_validator.py, hallucination_prevention.py, audit_agent_system.py, agent_orchestrator.py, five_w1h_agent.py, w5h1_*.py, real_data_audit_system.py, visualization_generator.py | `send_message`, `search_knowledge`, `refresh_insights` (NOTE: page unregistered) |
| Scheduler / Sync | scheduler_state.py, sync_monitor_state.py [orphan] | (none) | (none) | `start_schedulers` (called on app startup), `sync_tags`, `sync_realtime` |
| Tag admin     | viewer_tag_state.py, tag_hierarchy_state.py | (none — direct DB) | (none) | `toggle_dashboard`, `toggle_alarm`, `toggle_trend`, `toggle_model`, `add_tag`, `delete_tag`, `update_order` |

---

## 1. ALARM DOMAIN

### `AlarmsState` (states/alarms.py) — `/alarms` page
Parent: `rx.State`. 17 events (12 bg), 19 vars. Uses `AlarmService`.

| Member | Line | Type | Purpose | DB / Service |
|--------|------|------|---------|--------------|
| `filtered_alarms`            | 67  | @rx.var(cache=True) | filter+search alarms list | (in-memory) |
| `paginated_alarms`           | 105 | @rx.var | slice for current page | (in-memory) |
| `active_alarms`              | 112 | @rx.var | filter to unacknowledged | (in-memory) |
| `history_alarms`             | 118 | @rx.var | filter to acknowledged | (in-memory) |
| `active_count`/`history_count`/`active_total_pages`/`history_total_pages`/`total_pages`/`filtered_count`/`page_info`/`has_prev_page`/`has_next_page`/`selected_count`/`total_display`/`critical_display`/`warning_display`/`info_display`/`unacked_display` | 122-209 | @rx.var | stats/pagination | (in-memory) |
| `initialize`                 | 212 | @rx.event(bg) | initial load on page mount | AlarmService.get_rule_based_alarms |
| `_fetch_data`                | 239 | private async | fetch+statistics | AlarmService |
| `load_sensor_status`         | 319 | @rx.event(bg) | load sensor cards | SensorService |
| `refresh_data`               | 397 | @rx.event(bg) | reload alarm + sensors | AlarmService + SensorService |
| `set_hours_filter`           | 418 | @rx.event(bg) | change time range, reload | AlarmService |
| `toggle_show_acknowledged`   | 432 | @rx.event | bool toggle |  |
| `set_search_query`           | 440 | @rx.event(bg) | apply search filter |  |
| `set_severity_filter`        | 457 | @rx.event(bg) | apply severity filter |  |
| `set_status_filter`          | 470 | @rx.event(bg) | apply status filter |  |
| `set_view_mode`              | 483 | @rx.event(bg) | active|history toggle |  |
| `set_page`/`next_page`/`prev_page` | 496-515 | @rx.event/(bg) | pagination |  |
| `toggle_alarm_selection`/`select_all_visible`/`clear_selection` | 534-549 | @rx.event | selection mgmt |  |
| **`acknowledge_selected`**   | 555 | @rx.event(bg) | **DB write** — bulk ack | AlarmService.acknowledge_alarm × N |
| **`acknowledge_alarm`**      | 588 | @rx.event(bg) + `@event_with_error` decorator | **DB write** | AlarmService.acknowledge_alarm |

### `AlarmRTState` (states/alarm_rt_state.py) — `/alarms_rt`, `/alarms_rt_new`
Parent: `rx.State`. 7 events (7 bg). Direct raw SQL via `..db.q`.

| Member | Line | Type | Purpose | DB |
|--------|------|------|---------|-----|
| `on_load`                  | 49  | def     | mount hook |  |
| `load_all_data`            | 54  | @rx.event(bg) | aggregate load | influx_latest, influx_qc_rule, alarm_events |
| `load_sensor_status`       | 60  | @rx.event(bg) | per-sensor stat | influx_latest + qc rule |
| `refresh_realtime`         | 137 | @rx.event(bg) | refresh | (same) |
| `set_filter`/`set_scenario_filter` | 214,219 | def | filter |  |
| **`acknowledge_alarm`**    | 225 | @rx.event(bg) | **DB write** | alarm_events UPDATE |
| **`acknowledge_all`**      | 241 | @rx.event(bg) | **DB write — bulk** | alarm_events UPDATE |
| **`cleanup_old_alarms`**   | 256 | @rx.event(bg) | **DB delete/archive** | alarm_events DELETE |
| `toggle_auto_refresh`      | 271 | def |  |  |
| `start_auto_refresh`       | 278 | @rx.event(bg) | polling loop |  |

### `AlarmHistState` (states/alarm_hist_state.py) — `/alarms_hist`, `/alarms_hist_new`
Parent: `rx.State`. 9 events (3 bg), 0 vars. Raw SQL via `..db.q, execute_query`.

| Member | Line | Type | Purpose |
|--------|------|------|---------|
| `set_date_range`/`toggle_critical`/`toggle_warning`/`toggle_info`/`next_page`/`prev_page` | 62-94 | @rx.event | filter/paginate |
| `search_alarms`            | 82  | @rx.event(bg) | search |
| `on_load`                  | 100 | @rx.event(bg) | page mount |
| `fetch_history`            | 120 | @rx.event(bg) | DB read — alarm_events history with dynamic WHERE |
| `_fetch_statistics`        | 215 | private async | stats with SQL params |
| `set_start_date`/`set_end_date`/`set_quick_range`/`set_sensor_filter`/`set_scenario_filter`/`set_level_filter`/`toggle_unresolved`/`reset_filters`/`next_page`/`prev_page`/`set_page_size` | 250-322 | def | filter setters |
| **`export_excel`**         | 328 | async def | **file write** (Excel export) |

### `AlarmState` (states/alarm_state.py) — **ORPHAN**
Legacy unified rule+AI alarm state. 10 events (5 bg). Has DB write methods (`create_alarm_event`, `_save_alarm_vector`) and vector search. Document but skip for testing unless revived.

### `ScadaAlarmState` (states/scada_alarm_state.py) — `/scada-alarms`
Parent: `rx.State`. NO `@rx.event` decorators — uses plain `async def` methods triggered via on_mount/on_change. Implements Postgres LISTEN/NOTIFY for streaming alarms.

| Method | Line | Purpose |
|--------|------|---------|
| `initialize`               | 69  | mount hook |
| `load_alarm_logs`          | 74  | DB read — `scada_alarm_log` table |
| `_update_statistics`       | 110 | aggregate counts |
| `apply_filters`            | 174 | client-side filter |
| `toggle_streaming`/`start_streaming`/`stop_streaming` | 208-251 | LISTEN/NOTIFY control |
| `_keep_listening`          | 251 | **background task** — long-running NOTIFY listener |
| `_handle_notification`     | 262 | NOTIFY callback |
| `cleanup`                  | 292 | task cancellation |

### `ScadaAlarmComparisonState` (states/scada_alarm_comparison_state.py) — `/scada-alarm-comparison`
Parent: `rx.State`. 0 `@rx.event` decorators. Compares rule-based vs AI-based alarms.

| Method | Line | Purpose |
|--------|------|---------|
| `initialize`/`load_comparison_data`/`_calculate_statistics`/`generate_test_data` | 26-151 | comparison + test seed |

---

## 2. DASHBOARD / SENSOR DOMAIN

### `DashboardRealtimeState` (states/dashboard_realtime.py) — `/`
Parent: `BaseState`. 4 events (4 bg), 10 vars. Uses `SensorService` + raw ORM `ModelRegistry`/`Prediction` queries.

| Member | Line | Type | Purpose | DB |
|--------|------|------|---------|-----|
| `start_streaming`          | 69  | @rx.event(bg) | long-running streaming loop | SensorService |
| `stop_streaming`           | 119 | async def | stop loop |  |
| `_fetch_data`              | 130 | private async | data fetch | sensor + qc + statistics |
| `_fetch_forecast_data`     | 308 | private async | forecast overlay | ModelRegistry, Prediction (ORM) |
| `total_sensors`/`system_status`/`status_color`/`is_loading`/`formatted_sensors`/`critical_percentage_display`/`avg_deviation_display`/`max_alarm_display`/`warning_percentage`/`normal_percentage` | 362-438 | @rx.var | UI labels |  |
| `refresh_data`             | 441 | @rx.event(bg) | impl of BaseState abstract |  |
| `open_edit_dialog`/`close_edit_dialog`/`update_min_val`/`update_max_val`/`update_warning_low`/`update_warning_high`/`update_critical_low`/`update_critical_high` | 452-509 | def | edit dialog |  |
| **`save_sensor_info`**     | 513 | @rx.event(bg) | **DB write** — influx_qc_rule update | SensorService.update_sensor_metadata |
| `open_chart_dialog`/`load_chart_data`/`close_chart_dialog` | 556-593 | def/@rx.event(bg) | full-screen chart |  |

### `DashboardState` (states/dashboard/state.py) — *legacy, 1635 LOC*
Parent: `rx.State`. 40 events (4 bg), 18 vars. Only `components/features_table.py` and `components/indicators_table.py` import it (alias `D`). Not referenced from any page directly — likely deprecated by `DashboardRealtimeState`. Contains massive amount of chart toggle handlers (set_show_avg/min/max/etc. × dozens).

Selected high-priority handlers:
- `load` (230) — bg event, initial data fetch
- `start_realtime` (1132) — bg streaming loop
- `update_realtime_data` (1206) — bg
- `start_auto` (1084) — bg auto-refresh
- 30+ chart toggle handlers (set_show_*, toggle_*) — mostly trivial setters

### `DashboardRealtimeGroupedState` (states/dashboard_realtime_grouped.py) — **ORPHAN**
TagHierarchy-aware grouped dashboard. 1 bg event (`start_streaming_grouped`), 7 vars.

---

## 3. FORECAST DOMAIN

### `ForecastPlayerState` (states/forecast_player_state/state.py) — `/forecast`
Parent: `BaseState`. 9 events (9 bg), 57 vars. Uses `ForecastService`.

Background events (high-priority for testing):

| Method | Line | Purpose | DB / Side effect |
|--------|------|---------|------------------|
| `load_deployed_models`        | 933  | load deployed model list | ForecastService.get_deployed_models |
| `_load_playlist_internal`     | 991  | playlist data | ForecastService |
| `_load_predictions_internal`  | 1077 | predictions data | ForecastService.get_predictions |
| `load_predictions`            | 1240 | bg wrapper |  |
| `start_streaming`             | 1247 | 10-min countdown streaming loop | (long-running) |
| `load_forecast_steps`         | 1344 | step navigation data | ForecastService.get_forecast_steps |
| `_load_step_data_internal`    | 1377 | per-step data | ForecastService.get_step_data |
| `go_to_step`                  | 1422 | navigate to step |  |
| `load_initial_data`           | 1475 | mount hook |  |
| `load_selected_model_forecast`| 1484 | per-model | ForecastService |
| **`trigger_forecast_now`**    | 1499 | **DB write / side effect** — manual forecast run | ForecastService + scheduler |
| `start_countdown_monitor`     | 1566 | bg countdown |  |

Non-bg handlers: `select_model` (973), `stop_streaming` (1320), `toggle_playlist` (1325), `toggle_y_axis_scale` (1330), `select_from_playlist` (1335), step nav (1438-1453), `switch_to_playback_mode`/`switch_to_realtime_mode` (1458-1465), `set_selected_model_id` (1479), scheduler control (1553-1559).

57 `@rx.var` for chart data, table rows, countdown display, MAPE/R²/accuracy formatting (lines 75-916). All UI formatters, no DB.

---

## 4. TRAINING DOMAIN

### `TrainingState` (states/training_state/state.py) — base for wizard
Parent: `rx.State`. 7 events (7 bg), 5 vars. Uses `FeatureConfigService`. Has module-level cache in `states/training_state/cache.py` (`_training_cache`).

Background events:

| Method | Line | Purpose | DB / Side effect |
|--------|------|---------|------------------|
| `initialize`               | 120  | mount hook | FeatureConfigService.list_configs |
| `filter_configs_for_tag`   | 156  | filter for tag |  |
| `load_feature_config`      | 191  | load config | FeatureConfigService.get_complete_config |
| `set_new_config_name`      | 253  | name validation |  |
| **`create_feature_config`**| 303  | **DB write** | FeatureConfigService.create_feature_config + add_lag/rolling/temporal |
| **`start_training`**       | 364  | **long-running ML training** — fits model, evaluates, caches result | (no DB write itself — caches via `_cache_training_result`) |
| **`save_model`**           | 713  | **DB write** — persists trained model + predictions | model_registry + predictions tables |

Non-bg async: `set_selected_model` (172), `toggle_skip_features` (220), `toggle_feature_creator` (229), `toggle_rolling_feature` (288), `toggle_temporal_feature` (295), `reset_form` (1040), 6 parameter setters (1051-1089).

Computed vars: `horizons`, `forecast_summary`, `residuals_stats`, `config_name_validation_message`, `can_create_config`.

### `TrainingWizardState` (states/training_wizard_state.py) — `/training-wizard`
Parent: `TrainingState`. 2 events (2 bg), 37 vars (mostly display formatters).

| Method | Line | Purpose |
|--------|------|---------|
| `can_proceed`              | 21  | @rx.var — step gate logic |
| `validation_feasibility`   | 36  | @rx.var — walk-forward CV feasibility check |
| `next_step`/`previous_step`| 130-139 | wizard nav |
| `initialize_wizard`        | 149 | @rx.event(bg) — mount hook |
| `open_forecast_dialog`/`close_forecast_dialog` | 196-200 | dialog |
| `reset_wizard`             | 204 | reset |
| `start_wizard_training`    | 224 | wrapper → super().start_training |
| `monitor_training_completion` | 230 | @rx.event(bg) — polling |
| `navigate_to_performance`  | 639 | redirect |

Computed vars cover: raw/processed sample counts, feature counts, ARIMA params (AIC/BIC/AICC), residual stats (mean/std/skew/kurtosis), evaluation metrics (MAE/MAPE/RMSE/SMAPE/MASE), walk-forward stats, chart data (forecast/validation/ACF/PACF/QQ/histogram), table data, model_saved flag.

### `TrainingWizardStateEnhanced` (states/training_wizard_state_enhanced.py) — **ORPHAN**
Multi-inheritance: `TrainingWizardState, TagHierarchyState`. Adds tag hierarchy filtering. 6 events (1 bg), 5 vars. Not bound to any page.

---

## 5. COMMUNICATION DOMAIN

### `CommunicationState` (states/communication_state.py) — `/comm`
Parent: `rx.State`. 4 events (4 bg), 15 vars. Uses `CommunicationService` + pandas.

| Method | Line | Purpose | DB |
|--------|------|---------|-----|
| `load_data`                | 352 | @rx.event(bg) | CommunicationService.get_hourly_stats + get_daily_stats |
| `initialize`               | 357 | mount hook | CommunicationService.get_available_tags + load_data |
| `_fetch_data`              | 388 | private | hourly/daily/summary |
| `refresh_data`             | 443 | @rx.event(bg) |  |
| `set_selected_tag`         | 479 | @rx.event(bg) — change tag, reload |  |
| `set_selected_days_str`    | 486 | def |  |

15 `@rx.var` compute: `selected_days_str`, `chart_height`, `active_hours_str`, `total_hours_str`, `overall_success_rate` (capped at 100%, recent fix 2025-11-26), `total_records`, `expected_records`, `heatmap_matrix` (lines 104-158, complex aggregation), `hour_labels`, `date_labels`, `heatmap_dates`, `daily_chart_data`, `hourly_data`, `hourly_pattern_stats`, `anomaly_detection`.

---

## 6. TREND DOMAIN

### `TrendState` (states/trend_state.py) — `/trend`
Parent: `rx.State`. 17 events (7 bg), 16 vars. Uses `TrendService`.

Background events: `load` (58), `load_series_data` (96), `set_tag_select` (145), `set_aggregation_view` (152), `set_time_range` (171), `toggle_auto_refresh` (223), `auto_refresh_loop` (232).

Non-bg: `set_chart_mode` (191), `set_trend_selected` (199), `toggle_auto_scale` (208), `toggle_trend_composed_item` (213), pagination (`next_page`/`prev_page`/`set_page`/`set_page_size` 246-265).

**Side-effect events:**
- `export_csv_all` (271) — **file write** (CSV download)
- `export_csv_page` (304) — **file write**

Helpers: `_parse_time_range` (591), `_get_aggregation_table` (610), `_get_time_range_options` (628).

16 `@rx.var` for chart series, pagination, time labels, Y-axis domain, completeness/missing/average stats.

### `TrendStateEnhanced` (states/trend_state_enhanced.py) — **ORPHAN**
TagHierarchy-aware (multi-tag selection). 18 events (8 bg), 17 vars. Same shape as TrendState plus `on_tag_selected`/`on_tag_removed` handlers.

---

## 7. MODEL MANAGEMENT DOMAIN

### `ModelPerformanceState` (states/model_performance_state.py) — `/model-performance`
Parent: `rx.State`. 11 events (6 bg), 16 vars. Uses raw SQLAlchemy queries against `model_registry`.

| Method | Line | Purpose | DB |
|--------|------|---------|-----|
| `on_mount`                 | 46  | mount | (loads sensors+models) |
| `load_available_sensors`   | 51  | @rx.event(bg) | influx_tag DISTINCT |
| `load_performance_data`    | 83  | @rx.event(bg) | model history + drift + comparison |
| `_load_model_history`      | 125 | private | model_registry SELECT |
| `_load_drift_history`      | 165 | private | drift_history SELECT |
| `_calculate_model_comparison` | 193 | private | aggregation |
| `_get_current_models`      | 222 | private |  |
| `_calculate_summary`       | 251 | private |  |
| `set_selected_sensor`/`set_time_range`/`set_model_type`/`refresh_data` | 280-303 | @rx.event | setter/filter |
| `load_all_saved_models`    | 391 | @rx.event(bg) | model_registry full SELECT |
| **`deploy_model`**         | 502 | @rx.event(bg) | **DB write** — set is_deployed=True |
| `set_selected_model_for_deploy`/`undeploy_current_model` | 552-557 | def |  |
| **`delete_model`**         | 564 | @rx.event(bg) | **DB delete** — soft delete |
| `set_selected_model_for_delete` | 605 | def |  |
| **`undeploy_model`**       | 611 | @rx.event(bg) | **DB write** — set is_deployed=False |
| `navigate_to_forecast_player` | 987 | redirect |  |

16 `@rx.var`: deployed model info, recommendations, insights, algorithm comparison rows, best algorithm display, pipeline rows, training condition warnings.

### `ModelConfigState` (states/model_config_state.py) — **ORPHAN**
Parent: `rx.State`. 6 events (6 bg). Uses `ModelConfigService`. CRUD for model hyperparameters. Not bound to any page.

---

## 8. AI / RAG DOMAIN

### `AIState` (states/ai_state.py) — `/ai` page (UNREGISTERED — frontend orphan)
Parent: `rx.State`. 7 events (4 bg), 32 vars. Uses `AIService` + `ai_engine.rag_engine.get_rag_response`.

| Method | Line | Purpose | Engine |
|--------|------|---------|--------|
| `load`                     | 47  | @rx.event(bg) | mount — AIService.get_knowledge_base + get_ai_insights + initialize RAG |
| `send_message`             | 99  | @rx.event(bg) | chat — invokes `get_rag_response` from rag_engine, saves history via AIService.save_chat_history |
| `search_knowledge`         | 168 | @rx.event(bg) | AIService.search_knowledge |
| `refresh_insights`         | 194 | @rx.event(bg) | AIService.get_ai_insights |
| `clear_chat`/`clear_messages`/`load_initial_sensor_data` | 211-418 | @rx.event |  |
| `_extract_sensor_id`/`_prepare_context` | 217-225 | private |  |

32 `@rx.var` are all readers into a dict (`visualization_data`, `analysis_data`) — heavy chart data formatters.

### ai_engine modules (no direct State binding except via AIState)

| Module | Type | Inputs | Outputs | DB queries |
|--------|------|--------|---------|------------|
| `rag_engine.py` (RAGEngine) | RAG | query: str, use_w5h1: bool | response: str | `knowledge_base` SELECT, `qc_rules` SELECT, latest sensor — invoked via `..db.q` raw SQL |
| `rag_engine_pgvector.py` (PgVectorRAGEngine) | Vector RAG | query | top_k results | pgvector cosine sim on `knowledge_base.embedding` |
| `graph_rag_engine.py` (GraphRAGEngine) | Graph + vector RAG | query, sensor_tags | response | knowledge_base + sensor relations |
| `dynamic_rag_engine.py` (DynamicRAGEngine) | Dynamic RAG | query | response | DB lookup |
| `llamaindex_rag_engine.py` (LlamaIndexRAGEngine) | LlamaIndex wrapper | docs | indexed response |  |
| `knowledge_builder.py` | builder | (none) | int (count) | knowledge_base INSERT (bulk seed) |
| `knowledge_loader.py` | watcher | yaml files | KB rows | `KnowledgeFileWatcher` reloads on file change |
| `knowledge_search.py` (KnowledgeSearchEngine) | search | query, filters | results list | knowledge_base SELECT |
| `pandas_analysis_engine.py` (PandasAnalysisEngine) | analytics | sensors[], hours | AnalysisResult | influx_hist SELECT then pandas |
| `agent_orchestrator.py` | multi-agent | query | response | invokes ResearchAgent/AnalysisAgent/ReviewAgent |
| `audit_agent_system.py` (AuditAgent, RLSystem) | audit | agent runs | grades | agent_history table |
| `five_w1h_agent.py` (FiveW1HAgent) | structured prompt | query | 5W1H response |  |
| `hallucination_prevention.py` (HallucinationPrevention) | validator | response | ValidationResult |  |
| `response_validator.py` (ResponseValidator) | validator | response | AnalysisResponse |  |
| `visualization_generator.py` | chart spec | query+sensor+qc | viz dict |  |
| `w5h1_formatter.py` (W5H1Formatter) | formatter | data | W5H1Response |  |
| `w5h1_knowledge_retriever.py` | KB retriever | query | knowledge |  |
| `real_data_audit_system.py` (RealDataAuditSystem) | data gap | sensor, hours | DataGapAnalysis | influx_hist time-gap query |

**Trigger entry point:** All AI engine code is reachable only through `AIState` (used by `/ai` page, which is currently NOT registered in `ksys_app.py` per spec_01). Effectively dead from a UI test perspective.

**Earlier finding (security):** SQL injection vectors documented in `audit_security_2026-05-21.md` were in these engines (knowledge_search, pandas_analysis_engine). The full surface includes 12+ engines, most using raw `..db.q` with string interpolation.

---

## 9. SCHEDULER / SYNC DOMAIN

### `SchedulerState` (states/scheduler_state.py) — startup singleton
Parent: `rx.State`. 1 event (1 bg), 0 vars. Loaded from `ksys_app.py:204` to initialize APScheduler.

| Method | Line | Purpose |
|--------|------|---------|
| `start_schedulers`         | 27  | @rx.event(bg) — boots forecast/training schedulers |
| `stop_schedulers`          | 53  | async def — cleanup |

### `SyncMonitorState` (states/sync_monitor_state.py) — **ORPHAN**
Parent: `rx.State`. 4 events (4 bg). Manual sync triggers. Not bound to any page.

| Method | Line | Purpose |
|--------|------|---------|
| `refresh_data`             | 37  | @rx.event(bg) | sync status |
| `sync_tags`                | 148 | @rx.event(bg) | manual tag sync |
| `sync_realtime`            | 192 | @rx.event(bg) | manual rt sync |
| `sync_historical`          | 213 | @rx.event(bg) | manual hist sync |

---

## 10. TAG ADMIN DOMAIN

### `ViewerTagState` (states/viewer_tag_state.py) — `/viewer-tag`
Parent: `rx.State`. 10 events (10 bg), 0 vars. All DB writes via raw SQL.

| Method | Line | Purpose | DB |
|--------|------|---------|-----|
| `load_tags`                | 40  | @rx.event(bg) | viewer_tag SELECT |
| **`toggle_dashboard`**     | 109 | @rx.event(bg) | **DB write** UPDATE viewer_tag SET show_in_dashboard=... |
| **`toggle_alarm`**         | 126 | @rx.event(bg) | **DB write** |
| **`toggle_trend`**         | 143 | @rx.event(bg) | **DB write** |
| **`toggle_model`**         | 160 | @rx.event(bg) | **DB write** |
| **`update_order`**         | 181 | @rx.event(bg) | **DB write** UPDATE order |
| `open_add_dialog`/`close_add_dialog`/`set_add_tag_name` | 208-217 | def |  |
| **`add_tag`**              | 222 | @rx.event(bg) | **DB write** INSERT |
| **`delete_tag`**           | 267 | @rx.event(bg) | **DB delete** |
| **`show_all_dashboard`**   | 294 | @rx.event(bg) | **DB write** bulk update |
| **`hide_all_dashboard`**   | 310 | @rx.event(bg) | **DB write** bulk update |
| `clear_messages`           | 329 | def |  |

### `TagHierarchyState` (states/tag_hierarchy_state.py) — mixin
Parent: `BaseState`. 1 event (1 bg), 6 vars. Provides Station/System filtering used by *Enhanced states.

| Member | Line | Type | Purpose |
|--------|------|------|---------|
| `available_stations`/`available_systems`/`filtered_tags`/`station_tag_counts`/`system_tag_counts`/`selected_tags_by_station` | 43-148 | @rx.var | hierarchy facets |
| `load_tag_hierarchy`       | 149 | @rx.event(bg) | influx_tag SELECT with station/system parsing |
| `set_selected_station`/`set_selected_system`/`toggle_tag_selection`/`is_tag_selected`/`clear_selected_tags`/`select_top_tags`/`remove_selected_tag`/`select_all_in_system`/`get_tag_station`/`get_tag_system` | 217-271 | def | filter manipulation |

---

# Services Layer Inventory

## `BaseService` (services/base_service.py)
Constructor: `__init__(session: AsyncSession)`. Helpers: `execute_query`, `execute_scalar`, `execute_insert`.

## `AlarmService` (services/alarm_service.py)
| Method | Line | Returns | DB tables |
|--------|------|---------|-----------|
| `get_rule_based_alarms` | 22  | List[Dict] | alarm_events, influx_qc_rule |
| `get_active_sensor_alarms` | 213 | List[Dict] | influx_latest + qc |
| `get_alarm_statistics` | 357 | Dict | alarm_events aggregation |
| **`acknowledge_alarm`** | 453 | bool | **alarm_events UPDATE** |
| `_get_level_name` | 495 | str | (helper) |

## `SensorService` (services/sensor_service.py)
| Method | Line | Returns | DB tables |
|--------|------|---------|-----------|
| `get_all_sensors_with_latest` | 19  | List[Dict] | influx_latest, influx_tag |
| `get_aggregated_chart_data` | 95  | Dict | influx_agg_1m |
| `get_sensor_statistics` | 149 | Dict | influx_latest + qc |
| `get_sensor_chart_data` | 185 | List[Dict] | influx_hist |
| `_get_chart_color` | 257 | str | (helper) |
| `get_realtime_alarms_with_charts` | 266 | List[Dict] | influx_latest + qc + sliding window |
| `get_dashboard_statistics` | 300 | Dict | aggregation |
| **`update_sensor_metadata`** | 397 | None | **influx_qc_rule UPDATE / influx_tag UPDATE** |

## `ForecastService` (services/forecast_service.py)
| Method | Line | DB |
|--------|------|-----|
| `get_deployed_models` | 42 | model_registry SELECT |
| `get_predictions` | 104 | predictions SELECT |
| `get_latest_sensor_value` | 202 | influx_latest |
| `get_rolling_window_data` | 240 | influx_hist + predictions |
| `get_predictions_grouped` | 533 | predictions GROUP BY |
| `get_forecast_steps` | 708 | (predictions step calc) |
| `get_step_data` | 755 | actual + forecast merged |
| `get_timeline_chart_data` | 871 | timeline merged |

## `CommunicationService(BaseService)` (services/communication_service.py)
| Method | Line | DB |
|--------|------|-----|
| `get_available_tags` | 18 | influx_tag DISTINCT |
| `get_hourly_stats` | 34 | influx_agg_1m hourly bucket |
| `get_daily_stats` | 87 | influx_agg_1m daily bucket |
| `get_tag_summary` | 149 | aggregation |

## `TrendService` (services/trend_service.py)
| Method | Line | DB |
|--------|------|-----|
| `get_tags` | 17 | influx_tag |
| `get_series_data` | 34 | influx_agg_{1m,1h,1d} polymorphic |
| `get_realtime_data` | 116 | influx_latest |
| `get_statistics` | 158 | aggregation |

## `AIService` (services/ai_service.py)
| Method | Line | DB |
|--------|------|-----|
| `get_knowledge_base` | 17 | knowledge_base SELECT |
| `search_knowledge` | 52 | knowledge_base full-text |
| `get_sensor_context` | 112 | influx_latest + qc + alarms |
| **`save_chat_history`** | 184 | **chat_history INSERT** |
| `get_chat_history` | 211 | chat_history SELECT |
| `get_ai_insights` | 243 | aggregation |

## `ModelConfigService` (services/model_config_service.py)
CRUD for `model_registry`. Methods: get_model_schema, get_default_config, get_model_config, **save_model_config**, **create_model_config**, list_model_configs, **delete_model_config** (soft), **clone_model_config**, validate_config.

## `FeatureConfigService` family (3 versions: original / `_v2` / `_final`)
- `feature_config_service.py` (line 42) — original; example_usage script at line 559
- `feature_config_service_v2.py` (line 35) — version 2; example_usage at 509
- `feature_config_service_final.py` (line 17) — final (used by training_state)

CRUD for feature_config + lag/rolling/temporal/seasonal/fourier/diff/interaction features. ~14 methods each.

## `FeatureEngineeringService` (services/feature_engineering_service.py)
Pandas-based feature generation: lag, rolling, time, seasonal, advanced. Methods write back via `save_features_to_db`.

## `VirtualTagService` (services/virtual_tag_service.py)
Includes inner `FormulaParser` class (arithmetic/conditional/aggregation formula evaluation). Methods: get_active_virtual_tags, get_sensor_latest_values, get_sensor_aggregated_values, **calculate_arithmetic_tag**, **calculate_conditional_tag**, **calculate_aggregation_tag**, calculate_all_virtual_tags, **store_virtual_tag_values** (DB write), **calculate_and_store**.

⚠️ Security: `FormulaParser.parse_arithmetic` evaluates user-defined strings. Audit if any path is user-controlled.

---

# Test Priority Ranking

## Tier 1 — Mutating, business-critical (test FIRST)

| State | Handler | Why critical |
|-------|---------|--------------|
| AlarmsState | `acknowledge_alarm` (alarms.py:588) | Mutates alarm_events.acknowledged. ISA-18.2 audit trail. |
| AlarmsState | `acknowledge_selected` (alarms.py:555) | Bulk DB mutation. |
| AlarmRTState | `acknowledge_alarm` / `acknowledge_all` / `cleanup_old_alarms` (alarm_rt_state.py:225/241/256) | Bulk + delete; idempotency unclear. |
| ModelPerformanceState | `deploy_model` (502) / `undeploy_model` (611) / `delete_model` (564) | Production model toggling. |
| TrainingState | `save_model` (713) | Persists ML model + predictions; rolls forward forecast pipeline. |
| TrainingState | `start_training` (364) | Long-running ML run; resource leak/timeout risk. |
| TrainingState | `create_feature_config` (303) | DB write — multiple tables. |
| ForecastPlayerState | `trigger_forecast_now` (1499) | Manual forecast invocation; scheduler interaction. |
| DashboardRealtimeState | `save_sensor_info` (513) | Updates QC thresholds → cascades to alarm engine. |
| ViewerTagState | `toggle_dashboard` / `toggle_alarm` / `toggle_trend` / `toggle_model` / `update_order` / `add_tag` / `delete_tag` / `show_all_dashboard` / `hide_all_dashboard` (109-310) | Tag visibility cascades to all dashboards. |
| ScadaAlarmComparisonState | `generate_test_data` (151) | DB seed (likely admin-only — confirm). |

## Tier 2 — Long-running / background streaming (test for leak/timeout)

| State | Handler | Concern |
|-------|---------|---------|
| DashboardRealtimeState | `start_streaming` (69) | 30s loop, asyncio.wait_for with 28s timeout; verify no zombie task. |
| ForecastPlayerState | `start_streaming` (1247) | 600s loop; verify stop_streaming releases. |
| ForecastPlayerState | `start_countdown_monitor` (1566) | secondary loop; concurrency? |
| DashboardState | `start_realtime` (1132) | Per `_realtime_loop_id` guard — verify no double-loop. |
| DashboardState | `start_auto` (1084) | Same; verify guard. |
| BaseState | `start_polling` (40) | Abstract pattern; verify all subclasses implement `refresh_data` correctly. |
| TrendState | `auto_refresh_loop` (232) |  |
| AlarmsState | `initialize` polling + RT refresh — verify cancel-on-unmount |  |
| AlarmRTState | `start_auto_refresh` (278) |  |
| ScadaAlarmState | `_keep_listening` (251) | NOTIFY listener — must clean up DB conn on page leave. |
| SchedulerState | `start_schedulers` (27) | App-level singleton, runs forever. |
| TrainingState | `start_training` (364) | CPU-bound async — may block event loop. |

## Tier 3 — Read-mostly handlers (test for correctness)

All `load_*`, `refresh_*`, `set_*_filter`, computed `@rx.var`. Quick smoke tests; failures here = wrong data displayed but no corruption.

## Tier 4 — Side-effect writes to filesystem

| State | Handler |
|-------|---------|
| AlarmHistState | `export_excel` (328) — writes xlsx |
| TrendState | `export_csv_all` (271), `export_csv_page` (304) |

---

# Handlers Calling External Code

| Type | Handlers |
|------|----------|
| **OpenAI API call** | AIState.send_message → rag_engine.get_rag_response → RAGEngine._generate_openai_response (rag_engine.py:488); also PgVectorRAGEngine for embeddings (rag_engine_pgvector.py:97 _generate_missing_embeddings) |
| **APScheduler** | SchedulerState.start_schedulers, ForecastPlayerState.trigger_forecast_now |
| **Postgres LISTEN/NOTIFY** | ScadaAlarmState._keep_listening (raw asyncpg connection) |
| **pickle/joblib** | TrainingState.save_model + cache.py `_cache_training_result` (in-memory module dict — not on disk in current code) |
| **File watchers** | ai_engine/knowledge_loader.py `KnowledgeFileWatcher` (watchdog Observer) |

---

# Cross-Cutting Concerns

## Background event accounting
- Total `@rx.event(background=True)`: **112**
- Of those, ~10 are infinite loops (streaming / polling). The rest are single-shot bg tasks for DB I/O.
- Cancellation pattern: most use `while self.is_streaming:` + setter `stop_streaming()` — but no asyncio task tracking on most states (BaseState has `_polling_task: Optional[asyncio.Task]` declared but never assigned). Risk of zombie loops on page navigation.

## Service vs raw SQL split
- **Clean service layer:** AlarmsState, DashboardRealtimeState, ForecastPlayerState, CommunicationState, TrendState, AIState
- **Raw `..db.q` direct usage:** AlarmState, AlarmRTState, AlarmHistState, ScadaAlarmState, ScadaAlarmComparisonState, ViewerTagState, TagHierarchyState
- ai_engine modules: 100% raw SQL

The "Enhanced" orphans (AlarmsEnhancedState, TrendStateEnhanced, etc.) appear to be incomplete refactors toward the service pattern + TagHierarchy mixin.

## decorator `@event_with_error`
Imported from `ksys_app.utils.decorators` and used in `AlarmsState.acknowledge_alarm` (only). Comment claims it replaces try/except boilerplate "101× across 24 state files." Most state files still use inline try/except — adoption is partial.

## Module-level mutable state
- `ksys_app/states/training_state/cache.py` — `_training_cache: dict` — in-process cache for training results. Not serializable, lost on worker restart. No invalidation strategy in code reviewed.

---

# Recommended Test Plan Stub (input for next agent)

For a user who says "어떤 기능을 테스트해야 하는지 전혀 모르고 있음":

**Smoke (15 min):**
1. Visit each registered page (14 pages from spec_01) and confirm initial mount loads data.
2. Confirm 2 unregistered pages (`/ai`, `/design-system-demo`) are inaccessible.

**Functional (per Tier 1 handler, ~30 cases):**
1. Acknowledge alarm (rule-based, ISA-18.2) — `/alarms` + `/alarms_rt`. Confirm row turns acknowledged, DB updated.
2. Bulk acknowledge — `/alarms` select-all + acknowledge_selected.
3. Sensor metadata edit dialog — `/` → click sensor → edit → save. Confirm QC thresholds persist + alarm engine re-evaluates.
4. Tag visibility toggles — `/viewer-tag` → toggle each (dashboard/alarm/trend/model). Confirm cascades to corresponding page.
5. Add/delete tag — `/viewer-tag`.
6. Model deploy/undeploy/delete — `/model-performance`.
7. Trigger forecast now — `/forecast` → confirm new predictions inserted.
8. Run training wizard end-to-end — `/training-wizard` 6 steps, save model.
9. Export CSV — `/trend`.
10. Export Excel — `/alarms_hist`.

**Streaming/leak (30 min):**
1. Open `/` (dashboard), wait 3 polling cycles (90s). Navigate away. Confirm no zombie asyncio task / DB conn (check `pg_stat_activity`).
2. Same for `/forecast`, `/alarms_rt`, `/scada-alarms`.

**Edge / non-obvious:**
1. `acknowledge_alarm` idempotency — call twice, second should no-op or return False.
2. `start_streaming` race — refresh page rapidly, confirm no duplicate loops (DashboardState has `_realtime_loop_id` guard; verify others).
3. Walk-forward `validation_feasibility` (TrainingWizardState) — set training_days=1, horizon_hours=24, interval=10. Should return shortage error message.
4. `overall_success_rate` cap (CommunicationState:66) — confirm never exceeds 100% even with bad input data.
5. ScadaAlarmState NOTIFY — kill DB during streaming, confirm reconnect or graceful error.

---

## Path: `reports/spec_02_backend_states_services.md`
