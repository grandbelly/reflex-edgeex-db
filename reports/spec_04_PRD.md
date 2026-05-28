# KSYS — Reverse-Engineered Product Requirements Document (PRD)

> **Type:** Reverse-Engineered PRD (as-built, not as-designed)  
> **Source specs:** spec_01_frontend_pages.md · spec_02_backend_states_services.md · spec_03_database_schedulers.md  
> **Generated:** 2026-05-28  
> **Status:** Draft — Awaiting Engineering Sign-off

---

## Table of Contents

1. [Product Identity](#1-product-identity)
2. [Users & Personas](#2-users--personas)
3. [Feature Catalog by User Journey](#3-feature-catalog-by-user-journey)
4. [4-Perspective Value Table](#4-4-perspective-value-table)
5. [Feature Priority Matrix (M1 / M2 / M3)](#5-feature-priority-matrix-m1--m2--m3)
6. [Cleanup Recommendations](#6-cleanup-recommendations)
7. [Gaps vs Industry Expectations](#7-gaps-vs-industry-expectations)

---

## 1. Product Identity

KSYS is a **water treatment / desalination plant SCADA-adjacent monitoring and predictive analytics platform** — a web-based operational dashboard that ingests real-time IoT sensor data, evaluates threshold-based quality rules (QC) at 10-second intervals, generates and displays multi-horizon ML forecasts (Prophet / Auto-ARIMA / XGBoost) on a rolling 10-minute schedule, and provides an operator-facing alarm lifecycle from detection through acknowledgment through history query. The platform is deployed as a single-site Reflex (Python full-stack) application running in Docker on a Raspberry Pi, targeting a small operations team rather than an enterprise multi-plant deployment.

**Evidence (5 bullets):**

1. **`influx_qc_rule` table** stores `min_val`, `max_val`, `warning_low/high`, `critical_low/high` — standard process-variable safe-operating-range thresholds consistent with water treatment or desalination sensor monitoring (spec_03 §2.3).
2. **`RangeMonitor._initialize_thresholds()`** hard-codes `TMP` (막간차압, trans-membrane pressure) and `DP` (차압, differential pressure) — sensor names diagnostic of a **membrane-based desalination or filtration process** (spec_03 §6.4).
3. **Hardcoded virtual tags** `PRESSURE_DIFF`, `RECOVERY_RATE`, `OPERATING_TIME`, `TOTAL_PRODUCT_VOLUME_1H` in migration 08 (spec_03 §2.3) are standard desalination KPIs (recovery rate = product water / feed water).
4. **Alarm page** uses **ISA-18.2** priority vocabulary (P1 Advisory, P2 Caution, P3 Warning, P4 Emergency) — the dominant alarm management standard in process industries (water, oil & gas, chemical) (spec_01 §Page 2).
5. **`RPI_NODE_ID` environment variable** and single-site Docker deployment on Raspberry Pi suggest a **per-plant embedded controller**, not a cloud SAAS product (spec_03 §5 container architecture note).

---

## 2. Users & Personas

### 2.1 Persona A — Plant Operator

**Description:** On-shift control room operator monitoring live plant state, responding to alarms, and confirming sensor status. Limited ML or data analysis skill. Needs fast situational awareness.

| Dimension | Detail |
|-----------|--------|
| Top 3 jobs-to-be-done | 1. Know immediately when any sensor goes out of range. 2. Acknowledge alarms and document response (ISA-18.2 loop). 3. Verify that the real-time dashboard reflects current plant state. |
| Top 3 pages | `/` (Dashboard), `/alarms` (unified alarm dashboard), `/alarms_rt` (sensor card grid) |
| Success metrics | Alarm acknowledgment latency < 2 min; dashboard refresh cycle ≤ 30 s; zero missed P4 Emergency alarms per shift |

**Key event handlers used:** `DashboardRealtimeState.start_streaming` · `AlarmsState.acknowledge_alarm` · `AlarmsState.acknowledge_selected` · `AlarmRTState.acknowledge_alarm` · `AlarmsState.set_hours_filter`

---

### 2.2 Persona B — Data Analyst / Process Engineer

**Description:** Engineer reviewing historical trends, investigating anomalies, training and evaluating ML models, and exporting data for reports. Needs drill-down capability and configurable views.

| Dimension | Detail |
|-----------|--------|
| Top 3 jobs-to-be-done | 1. Plot historical sensor data at adjustable aggregation to diagnose process changes. 2. Train and compare ML models for sensor value forecasting. 3. Export clean time-series data for off-platform analysis. |
| Top 3 pages | `/trend` (trend analysis + CSV export), `/training-wizard` (6-step ML training), `/model-performance` (algorithm comparison) |
| Success metrics | CSV export completes in < 10 s for 30-day datasets; training wizard 6-step flow completes without error; MAPE of deployed model < 10% on validation set |

**Key event handlers used:** `TrendState.load_series_data` · `TrendState.export_csv_all` · `TrainingWizardState.start_wizard_training` · `TrainingState.save_model` · `ModelPerformanceState.deploy_model`

---

### 2.3 Persona C — System Administrator

**Description:** Technical administrator configuring sensor visibility, deploying/reverting ML models, monitoring data sync health, and managing tag metadata. Has DB access or equivalent technical authority.

| Dimension | Detail |
|-----------|--------|
| Top 3 jobs-to-be-done | 1. Control which tags appear on each screen (dashboard / alarm / trend / model). 2. Deploy the best-performing trained model so forecasts run automatically. 3. Investigate communication quality or data-sync failures. |
| Top 3 pages | `/viewer-tag` (tag visibility admin), `/model-performance` (deploy/undeploy/delete), `/comm` (communication success rate) |
| Success metrics | Tag visibility toggle persists immediately; model deployment triggers forecast within next 10-min cycle; communication heatmap shows ≥ 95% success rate as baseline |

**Key event handlers used:** `ViewerTagState.toggle_dashboard/alarm/trend/model` · `ViewerTagState.add_tag` · `ViewerTagState.delete_tag` · `ModelPerformanceState.deploy_model` · `ModelPerformanceState.undeploy_model` · `ModelPerformanceState.delete_model` · `DashboardRealtimeState.save_sensor_info`

---

## 3. Feature Catalog by User Journey

---

### 3.1 Monitor Real-Time Plant State

**Pages:** `/` (Dashboard) · `/alarms_rt` · `/alarms_rt_new`

**Description:** The primary operational view. The dashboard shows all configured sensors as a status table with NORMAL / WARNING / CRITICAL badges, risk bars, and live values refreshed every 30 seconds via a WebSocket streaming loop.

| Item | Detail |
|------|--------|
| Key event handlers | `DashboardRealtimeState.start_streaming` (bg loop, 30s) · `DashboardRealtimeState._fetch_data` · `DashboardRealtimeState.save_sensor_info` (edit QC thresholds inline) |
| DB tables touched | `influx_latest` (view on `influx_hist`) · `influx_qc_rule` · `influx_tag` · `model_registry` (forecast overlay) · `predictions` (overlay) |
| Expected output | Live sensor table with status badges; risk bar per row; system-level KPI summary (total / normal / warning / critical counts) |
| Known issues | `/alarms_rt` and `/alarms_rt_new` are duplicate pages for the same `AlarmRTState`; filter bar is hardcoded (not wired to state) on both; "Load More" / "Next" pagination buttons are dead (spec_01 Issues 2, 3, 4) |

---

### 3.2 Investigate and Acknowledge Alarms

**Pages:** `/alarms` · `/alarms_rt` · `/alarms_rt_new`

**Description:** Operator-facing alarm lifecycle. Active view shows current threshold violations; History view supports ISA-18.2 priority filtering, time-range selection, search, and paginated acknowledgment.

| Item | Detail |
|------|--------|
| Key event handlers | `AlarmsState.acknowledge_alarm` (line 588) · `AlarmsState.acknowledge_selected` (line 555) · `AlarmsState.set_hours_filter` · `AlarmsState.set_severity_filter` · `AlarmsState.set_search_query` · `AlarmRTState.acknowledge_alarm` (line 225) · `AlarmRTState.acknowledge_all` (line 241) · `AlarmRTState.cleanup_old_alarms` (line 256) |
| DB tables touched | `alarm_history` (acknowledge UPDATE, history SELECT) · `influx_latest` (active sensor status) · `influx_qc_rule` |
| Expected output | ISA-18.2 P1–P4 priority cards; alarm rows with acknowledged/unacknowledged status; bulk-ack capability; paginated history with search |
| Alarm generation | `AlarmMonitor` (10s loop) writes to `alarm_history`, sends `pg_notify('alarm_event')` → `DatabaseEventListener` → frontend push |

---

### 3.3 Query Alarm History

**Pages:** `/alarms_hist` · `/alarms_hist_new` · `/alarms` (History tab)

**Description:** Historical alarm query for post-shift or investigation purposes. Date-range picker, severity checkbox filters, and pagination.

| Item | Detail |
|------|--------|
| Key event handlers | `AlarmHistState.fetch_history` (line 120) · `AlarmHistState.search_alarms` · `AlarmHistState.set_date_range` · `AlarmHistState.toggle_critical/warning/info` · `AlarmHistState.export_excel` (line 328 — xlsx file write) |
| DB tables touched | `alarm_history` (SELECT with dynamic WHERE + pagination) |
| Expected output | Filterable alarm list; stat cards (total / most-triggered sensor / avg level / resolution rate); Excel export download |
| Known issues | Two near-duplicate pages `/alarms_hist` and `/alarms_hist_new` backed by same state (spec_01 Issue 4) |

---

### 3.4 Analyze Historical Sensor Trends

**Pages:** `/trend`

**Description:** Engineering drill-down into time-series sensor data. Supports 4 aggregation levels (1m / 10m / 1h / 1d), multiple chart types, brush range-sync between top and bottom chart, and CSV export.

| Item | Detail |
|------|--------|
| Key event handlers | `TrendState.load_series_data` · `TrendState.set_tag_select` · `TrendState.set_aggregation_view` · `TrendState.set_time_range` · `TrendState.export_csv_all` (line 271) · `TrendState.export_csv_page` (line 304) |
| DB tables touched | `influx_tag` (tag list) · `influx_agg_1m` / `influx_agg_10m` / `influx_agg_1h` / `influx_agg_1d` (continuous aggregates) · `influx_latest` (real-time overlay) |
| Expected output | Area/Line/Bar chart with brush zoom; data completeness badge; missing-data rows highlighted in red; CSV download (all data or current page) |

---

### 3.5 Train ML Forecasting Model

**Pages:** `/training-wizard` (6-step wizard)

**Description:** Guided offline model training flow. Engineer selects a sensor, picks an algorithm (Prophet / Auto-ARIMA / XGBoost), configures lag/rolling/temporal feature engineering, sets walk-forward cross-validation parameters, triggers training, and saves the resulting model to the registry.

| Item | Detail |
|------|--------|
| Wizard steps | Step 1: Sensor selection · Step 2: Algorithm selection · Step 3: Feature config (lag/rolling/temporal) · Step 4: Training params (walk-forward CV) · Step 5: Execute training · Step 6: Results (MAPE/R², fold table, residual diagnostics, ACF/PACF) |
| Key event handlers | `TrainingState.create_feature_config` (line 303) · `TrainingState.start_training` (line 364) · `TrainingState.save_model` (line 713) · `TrainingWizardState.start_wizard_training` · `TrainingWizardState.monitor_training_completion` |
| DB tables touched | `influx_hist` (training data read) · `feature_store` (engineered features write) · `model_registry` (model pickle + metrics write) · `predictions` (offline backtest write) · `training_evaluation` (fold results write) |
| Expected output | Trained model stored in `model_registry.model_pickle`; performance charts (fold MAPE, residuals histogram, QQ plot, ACF/PACF); model ready for deployment |
| Service layer | `FeatureConfigService` (final version) · `FeatureEngineeringService` · module-level `_training_cache` (in-memory, lost on restart) |

---

### 3.6 Manage Deployed Forecast Models

**Pages:** `/model-performance` · `/forecast` (deploy confirmation panel)

**Description:** Administrator view for comparing trained models per sensor, deploying the best model, undeploying the active one, and deleting old models.

| Item | Detail |
|------|--------|
| Key event handlers | `ModelPerformanceState.deploy_model` (line 502) · `ModelPerformanceState.undeploy_model` (line 611) · `ModelPerformanceState.delete_model` (line 564) · `ModelPerformanceState.load_all_saved_models` |
| DB tables touched | `model_registry` (is_deployed UPDATE · soft DELETE) · `drift_monitoring` (drift history read) · `prediction_performance` (accuracy read) |
| Expected output | Algorithm MAPE comparison bar chart; "Best Algorithm" highlight card; saved models table with Deploy buttons; currently deployed model card; top-3 ML pipeline detail cards |
| Downstream effect | Setting `is_deployed=TRUE` causes `ForecastScheduler` to include model in next 10-min forecast run |

---

### 3.7 View Live Forecast Predictions

**Pages:** `/forecast`

**Description:** Online ML prediction player showing rolling-window chart (past actual + predicted + confidence interval), MAPE/NRMSE accuracy cards, horizontal data table, and scheduler countdown.

| Item | Detail |
|------|--------|
| Key event handlers | `ForecastPlayerState.load_deployed_models` · `ForecastPlayerState.select_model` · `ForecastPlayerState.load_predictions` · `ForecastPlayerState.trigger_forecast_now` (line 1499 — manual run) · `ForecastPlayerState.start_countdown_monitor` |
| DB tables touched | `forecast_player_cache` (primary read — pre-computed JSONB) · `model_registry` (deployed list) · `predictions` (raw predictions fallback) |
| Expected output | Composed chart with T0 red line, past zone (blue), future zone (orange/green); MAPE / NRMSE / accuracy metric cards; horizontal table (actual vs predicted, absolute and relative error per time point); next-prediction countdown |
| Background data flow | `ForecastScheduler` (10 min) → writes `predictions` + `forecast_player_cache` → UI reads `forecast_player_cache` on next refresh |

---

### 3.8 Compare Rule-Based vs AI Alarm Methods

**Pages:** `/scada-alarm-comparison` · `/scada-alarms`

**Description:** Diagnostic view comparing classical threshold-rule alarms against AI-based alarm detection for the same time window. Supports evaluating whether the AI alarm engine adds value over fixed rules.

| Item | Detail |
|------|--------|
| Key event handlers | `ScadaAlarmComparisonState.load_comparison_data` · `ScadaAlarmComparisonState.generate_test_data` (DB seed — admin only) · `ScadaAlarmState.load_alarm_logs` · `ScadaAlarmState.toggle_streaming` (Postgres LISTEN/NOTIFY) |
| DB tables touched | `scada_alarm_log` (SCADA source alarm log) · `alarm_history` (system-generated alarms) |
| Expected output | Dual table view (rule-based blue badges / AI-based purple badges); stat cards for counts per method; real-time SCADA alarm log with severity filter |

---

### 3.9 Monitor Sensor Communication Quality

**Pages:** `/comm`

**Description:** Operational diagnostic showing data collection completeness per sensor per hour, surfacing communication failures between the upstream data source and the local database.

| Item | Detail |
|------|--------|
| Key event handlers | `CommunicationState.initialize` · `CommunicationState.set_selected_tag` · `CommunicationState.set_selected_days_str` · `CommunicationState.refresh_data` |
| DB tables touched | `influx_tag` (available tags) · `influx_agg_1m` (hourly record count vs expected count) |
| Expected output | Hourly heatmap grid (color = success rate); daily trend area chart with 95% reference line; overall success rate stat |
| Known issue | `overall_success_rate` is capped at 100% via code fix dated 2025-11-26 (spec_02 CommunicationState vars) |

---

### 3.10 Configure Sensor Tag Visibility

**Pages:** `/viewer-tag`

**Description:** Admin panel controlling which tags appear on each screen. Toggle switches per tag per screen (dashboard / alarm / trend / model). Changes propagate immediately via DB-level view filtering.

| Item | Detail |
|------|--------|
| Key event handlers | `ViewerTagState.toggle_dashboard/alarm/trend/model` · `ViewerTagState.update_order` · `ViewerTagState.add_tag` · `ViewerTagState.delete_tag` · `ViewerTagState.show_all_dashboard` / `hide_all_dashboard` |
| DB tables touched | `viewer_tag` (UPDATE show_* columns) — changes immediately affect `influx_latest`, `influx_latest_alarm`, `influx_latest_trend`, `influx_latest_model` views |
| Expected output | Tag table with toggle switches; add/delete dialog; bulk show-all / hide-all for dashboard |
| Cascade impact | Disabling a tag on "dashboard" removes it from `influx_latest` view → disappears from Dashboard and Alarms pages immediately |

---

### 3.11 AI Chat Sensor Insights — CURRENTLY DEAD (Gap)

**Pages:** `/ai` — **NOT REGISTERED in `ksys_app.py` (spec_01 §Dead Pages)**

**Description:** A full chat interface backed by a multi-RAG-engine AI layer (pgvector, GraphRAG, LlamaIndex, 5W1H agent, hallucination prevention). The implementation is complete on the backend (`AIState`, `AIService`, 18 `ai_engine` modules) but the page module is never imported into the app, making the route return 404.

| Item | Detail |
|------|--------|
| Why dead | `pages/ai_insights.py` defines `@rx.page("/ai")` but is not imported in `ksys_app/ksys_app.py` (spec_01 line 37). `ENABLE_AI_FEATURES` env guard exists but the import itself is missing. |
| Backend readiness | `AIState` (7 events, 32 vars) · `AIService` · `rag_engine.py` (OpenAI API) · `rag_engine_pgvector.py` · `graph_rag_engine.py` · `agent_orchestrator.py` · `audit_agent_system.py` · `five_w1h_agent.py` · 5 additional engine modules |
| DB tables touched | `knowledge_base` · `chat_history` · `influx_latest` · `influx_qc_rule` (would be used if activated) |
| Resolution path | Add `from ksys_app.pages import ai_insights` to `ksys_app.py` conditionally gated by `ENABLE_AI_FEATURES` env var |

---

## 4. 4-Perspective Value Table

| Perspective | Description |
|-------------|-------------|
| **Problem** | Plant operators at a small desalination / water treatment site have no integrated tool to simultaneously monitor real-time sensor health, act on threshold alarms, review historical trends, and predict near-future sensor values. Anomalies are discovered late; alarm fatigue increases from unfiltered raw alerts; model performance degrades silently. |
| **Solution** | KSYS provides a unified web dashboard that combines real-time sensor monitoring (30s refresh), ISA-18.2-compliant alarm management with acknowledgment, historical trend analysis with CSV export, online ML forecast at 10-minute intervals, and a guided wizard for retraining and deploying new models — all accessible from a single Reflex application on the plant network. |
| **Functional UX Effect** | Operators see plant state at a glance through color-coded status badges and risk bars, acknowledge alarms directly in the UI, drill into any sensor's 30-day history with configurable aggregation, and view forecast confidence intervals for proactive decision support — without switching tools or requiring data-science expertise. |
| **Core Value** | Reduced time-to-alarm-response, evidence-based model-driven early warning of impending threshold violations, and a complete audit trail from alarm generation through acknowledgment — lowering operational risk at a site where process uptime directly affects water production volume. |

---

## 5. Feature Priority Matrix (M1 / M2 / M3)

### M1 — Must Work Correctly (Production-Critical)

| Feature | Pages / Handlers | Rationale |
|---------|-----------------|-----------|
| Real-time sensor monitoring | `/` · `DashboardRealtimeState.start_streaming` | Core situational awareness; 30s data staleness = blind to live anomalies |
| Alarm generation pipeline | `AlarmMonitor` 10s loop → `alarm_history` INSERT → `pg_notify` | ISA-18.2 compliance; missed alarm = safety / compliance risk |
| Alarm acknowledgment | `AlarmsState.acknowledge_alarm` · `AlarmRTState.acknowledge_alarm` | Operator action record; required for shift handover and audit |
| Bulk alarm acknowledgment | `AlarmsState.acknowledge_selected` · `AlarmRTState.acknowledge_all` | Efficient recovery from multi-alarm events |
| QC threshold persistence | `DashboardRealtimeState.save_sensor_info` → `SensorService.update_sensor_metadata` | Changes must persist to `influx_qc_rule`; wrong thresholds → wrong alarms |
| Forecast scheduler (10-min cycle) | `ForecastScheduler` · `predictions` table | Core predictive feature; model deployed → predictions must flow |
| Actual value backfill | `ActualValueUpdater` | Without backfill, MAPE metrics are NULL; accuracy display is broken |
| Model deploy / undeploy | `ModelPerformanceState.deploy_model` · `undeploy_model` | Gate on forecast pipeline; setting `is_deployed=TRUE` activates live forecasting |
| Tag visibility control | `ViewerTagState` all DB-write handlers | Controls what data all other pages show; misconfigured = empty dashboards |
| Continuous aggregates | `influx_agg_1m/10m/1h/1d` (TimescaleDB) | Underpins Trend, Communication, and Forecast pages; stale = broken charts |

---

### M2 — Important But Not Critical

| Feature | Pages / Handlers | Rationale |
|---------|-----------------|-----------|
| 6-step training wizard | `/training-wizard` · `TrainingState.start_training` + `save_model` | Needed to retrain models when data distribution drifts; not needed for daily operation |
| Historical trend analysis + CSV export | `/trend` · `TrendState.export_csv_all` | Engineering analysis and data extraction; not real-time critical |
| Alarm history query + Excel export | `/alarms_hist` · `AlarmHistState.fetch_history` + `export_excel` | Post-shift investigation; important but asynchronous |
| Communication quality heatmap | `/comm` · `CommunicationState` | Diagnostic tool for data ingestion health; needed weekly not per-shift |
| Model performance comparison | `/model-performance` · algorithm comparison chart | Needed before deploying a new model; not a continuous-use feature |
| SCADA alarm comparison | `/scada-alarm-comparison` · `/scada-alarms` | Valuable for tuning alarm strategy; not a per-shift requirement |
| Forecast player — manual trigger | `/forecast` · `ForecastPlayerState.trigger_forecast_now` | On-demand forecast run; useful for testing, not production-critical |
| Virtual tag scheduler | `VirtualTagScheduler` + `pg_cron` | KPIs like `RECOVERY_RATE` depend on this; if stopped, derived KPI sensors go stale |
| Performance aggregator | `PerformanceAggregator` (hourly) | Feeds model-performance page; degraded metrics display if stopped but forecasts still run |

---

### M3 — Nice-to-Have or Currently Broken

| Feature | Pages / Handlers | Rationale |
|---------|-----------------|-----------|
| `/ai` — AI chat sensor insights | `AIState` · `ai_engine/` (18 modules) | **Dead route (404)**. Backend complete; page not registered. Requires single import to activate. |
| `/design-system-demo` | `design_system_demo.py` | **Dead route (404)**. Developer-only component showcase. Zero user impact. |
| `/alarms_rt_new` (duplicate) | Same `AlarmRTState` as `/alarms_rt` | Parallel version under active development; filter bar still hardcoded; "Next" pagination dead. |
| `/alarms_hist_new` (duplicate) | Same `AlarmHistState` as `/alarms_hist` | Similar — improved UX in progress; functional parity not yet reached. |
| `DailyTrainingScheduler` | `schedulers/daily_training.py` | Code exists but **not wired into `SchedulerManager.start_all()`** — never runs. Intended for nightly automatic retraining. |
| `SyncMonitorState` | `states/sync_monitor_state.py` | Orphan — no page binds this state; manual sync monitoring has no UI. |
| `TrendStateEnhanced` / multi-tag trend | `states/trend_state_enhanced.py` | Orphan — partially developed TagHierarchy-aware multi-sensor trend. Not surfaced in any page. |
| `AlarmsEnhancedState` | `states/alarms_enhanced.py` | Orphan — TagHierarchy-aware alarm state. In-progress refactor, not activated. |
| `DashboardRealtimeGroupedState` | `states/dashboard_realtime_grouped.py` | Orphan — grouped-sensor dashboard variant. Not activated. |
| Forecast step navigation | `ForecastPlayerState.go_to_step` · `load_forecast_steps` | UI for navigating individual forecast horizons exists but is secondary to the main chart view. |
| `overall_success_rate` cap | `CommunicationState` (line 66) | Fixed 2025-11-26; regression test should confirm cap at 100% holds. |

---

## 6. Cleanup Recommendations

The following actions are ordered by effort-to-impact ratio (quickest wins first).

---

### CR-01: Register `/ai` route or formally disable it

**Action:** Add `from ksys_app.pages import ai_insights` to `ksys_app/ksys_app.py`, guarded by `if os.getenv("ENABLE_AI_FEATURES", "false").lower() == "true":`  
**Effort:** 0.5h (code) + 1h (smoke test with `ENABLE_AI_FEATURES=true`)  
**Regression risk:** Low — the page was written in isolation; no other page imports `AIState`  
**Alternative if AI is out-of-scope:** Delete `pages/ai_insights.py`, `states/ai_state.py`, `services/ai_service.py`, `components/ai_visualizations.py`, and the entire `ai_engine/` directory. This removes ~5,000 lines of unreachable code including known SQL injection vectors in `knowledge_search.py` and `pandas_analysis_engine.py` (spec_02 §AI/RAG Domain security note).

---

### CR-02: Pick canonical realtime alarm page and redirect the other

**Action:** Choose one of `/alarms_rt` or `/alarms_rt_new` as the production route. Wire the filter bar (`on_search`, `on_severity_change`, `on_status_change` props) to `AlarmRTState` setters. Implement the "Load More" / "Next" pagination handler (`AlarmRTState` has `start_auto_refresh` bg loop but no page-offset model). Redirect the abandoned route to the canonical one or remove it.  
**Effort:** 3–4h (fix filter wiring + pagination) + 1h (redirect)  
**Regression risk:** Medium — both pages share `AlarmRTState`; state mutation changes affect both until one is removed  
**Evidence:** spec_01 Issues 2, 3, 4; spec_01 page 3 note "filter_bar is rendered with hardcoded `search_value=\"\"`"

---

### CR-03: Pick canonical alarm history page and redirect the other

**Action:** Same as CR-02 applied to `/alarms_hist` vs `/alarms_hist_new`. The `/alarms_hist_new` version has a better UX (quick-select buttons, severity checkboxes) and should be the canonical route.  
**Effort:** 1h (remove `/alarms_hist`, add redirect)  
**Regression risk:** Low — the two pages share `AlarmHistState`; one can be deleted without state change

---

### CR-04: Merge `trend_state.py` and `trend_state_enhanced.py`

**Action:** `TrendStateEnhanced` extends `TrendState` with `TagHierarchyState` multi-tag support (spec_02 §TrendStateEnhanced). The two are ~90% identical. If multi-tag trend analysis is desired, promote `TrendStateEnhanced` to the active state in `trend_enhanced_v2.py`. If not, delete `trend_state_enhanced.py`.  
**Effort:** 2h (page binding change + test) or 0.5h (delete)  
**Regression risk:** Medium if promoting (new mixin may cause unexpected state inheritance); Low if deleting

---

### CR-05: Wire `DailyTrainingScheduler` into `SchedulerManager`

**Action:** `schedulers/daily_training.py` is written but never called from `SchedulerManager.start_all()` (spec_03 §5.6). Add it to the scheduler chain. Activating it enables automatic nightly model retraining, which feeds the forecast pipeline without manual wizard runs.  
**Effort:** 1h (add to scheduler manager + environment gate)  
**Regression risk:** Medium — first activation may trigger unexpected training runs if `is_deployed` models exist; recommend gating behind `ENABLE_DAILY_TRAINING` env var

---

### CR-06: Fix `AlarmRTState` hardcoded filter literals in `/alarms_rt`

**Action:** `alarms_rt_simple.py` calls `filter_bar(search_value="", severity_filter="all", status_filter="all")` with string literals instead of state vars. Wire to `AlarmRTState.search_query`, `AlarmRTState.severity_filter`, `AlarmRTState.status_filter` (spec_01 Issue 2).  
**Effort:** 1h  
**Regression risk:** Low — additive change; no DB writes

---

### CR-07: Delete `design_system_demo.py`

**Action:** The file defines `@rx.page(route="/design-system-demo")` but is never imported (spec_01 §Dead Pages). It is a developer reference, not user-facing.  
**Effort:** 0.25h (delete file + confirm no imports)  
**Regression risk:** None

---

### CR-08: Consolidate `feature_config_service` family (3 versions)

**Action:** Three files exist: `feature_config_service.py`, `feature_config_service_v2.py`, `feature_config_service_final.py`. Only `_final` is imported by `training_state/state.py` (spec_02 §Services). Delete the two legacy versions.  
**Effort:** 0.5h (verify no other imports + delete)  
**Regression risk:** Low — confirm grep shows zero non-test imports before deleting

---

### CR-09: Create a `/sync` page binding `SyncMonitorState`

**Action:** `SyncMonitorState` has 4 background event handlers (`sync_tags`, `sync_realtime`, `sync_historical`, `refresh_data`) but no UI page. Without a UI, administrators cannot manually trigger sync or see sync status (spec_02 §SyncMonitorState).  
**Effort:** 3–4h (create page, add to `ksys_app.py`, add nav link)  
**Regression risk:** Low — new page only

---

## 7. Gaps vs Typical SCADA / IoT Industry Expectations

---

### Gap 1: No User Authentication

**Finding:** Zero of 201 `@rx.event` handlers check a user session, token, or role. Any user who can reach the network can access all pages, perform alarm acknowledgment, deploy/delete ML models, and modify sensor QC thresholds. There is no login page, no session state, and no middleware.  
**Evidence:** spec_02 §Cross-Cutting Concerns — "179 events with no auth" (originally noted in audit; 201 total handlers none of which call an auth guard).  
**Industry expectation:** IEC 62443 (industrial cybersecurity) and NIST SP 800-82 require authentication for HMI access. ISA-18.2 alarm management assumes operator identity for the `acknowledged_by` field — currently this field would be NULL or a hardcoded string.  
**Risk level:** High for any internet-accessible deployment; medium for air-gapped LAN.

---

### Gap 2: No Role-Based Access Control (RBAC)

**Finding:** All pages and all event handlers are accessible to all users. There is no differentiation between Operator (read + acknowledge), Engineer (train + configure), and Admin (deploy + delete + tag management).  
**Evidence:** spec_01 §Master Route Table — 14 routes, none gated. spec_02 shows destructive handlers (`delete_model`, `cleanup_old_alarms`, `generate_test_data`) with no role check.  
**Industry expectation:** SCADA platforms (OSIsoft PI, Wonderware, Ignition) enforce role separation; alarm acknowledgment is typically Operator-level, model deployment is Engineer/Admin-level.

---

### Gap 3: No Operator Action Audit Log (Beyond Alarms)

**Finding:** `alarm_history.acknowledged_by` provides a partial audit trail for alarm acknowledgments, but the field is likely NULL or a fixed string since there is no user authentication (Gap 1). No other operator actions (model deployment, sensor threshold edit, tag visibility change) are logged.  
**Evidence:** spec_03 §2.3 shows `alarm_history` has `acknowledged_by VARCHAR` and `acknowledged_at TIMESTAMPTZ` — but these can only be meaningful if the user identity is captured. `DashboardRealtimeState.save_sensor_info` writes to `influx_qc_rule` with no write-log table. `ModelPerformanceState.deploy_model` sets `deployed_by` in `model_registry` (spec_03 §2.3) but the value would come from an unauthenticated session.  
**Industry expectation:** 21 CFR Part 11 (pharma), FDA, and water treatment regulations require tamper-evident audit logs of configuration changes.

---

### Gap 4: No Multi-Plant / Multi-Tenant Support

**Finding:** The system is hard-coded for a single plant. Table schemas have no `plant_id` or `site_id` column. `RPI_NODE_ID` env var suggests per-site differentiation at the infrastructure level, but not at the data model level.  
**Evidence:** spec_03 §2.3 `influx_hist`, `influx_qc_rule`, `model_registry` — no site partition column. `RangeMonitor._initialize_thresholds()` hard-codes sensor names for a specific plant (spec_03 §6.4).  
**Industry expectation:** Commercial SCADA SaaS (Samsara, Aveva, Osisoft Cloud Services) support multi-facility views. Even on-premise Ignition supports enterprise-level multi-plant tags.

---

### Gap 5: No Mobile-Responsive Design

**Finding:** The UI has not been tested for mobile viewports. Playwright tests referenced in project history (spec introduction mentions "Playwright tested desktop only"). The Reflex framework generates React components that may not adapt to small screens without explicit responsive CSS.  
**Evidence:** spec_01 §Page 3 notes "responsive 2→6 column card grid for all sensors" on `/alarms_rt` as the only explicit responsive annotation — the rest of the app is untested on mobile.  
**Industry expectation:** Plant operators increasingly use tablets for walkabout inspections. Ignition Perspective and similar modern SCADA platforms are mobile-first.

---

### Gap 6: Mixed Korean / English UI (No i18n Framework)

**Finding:** Page titles, button labels, and column headers use a mixture of Korean and English with no internationalization library. Korean strings are hardcoded directly in Python source files.  
**Evidence:** spec_01 route table — "실시간 알람 상태" · "알람 이력 분석" alongside "Trend Analysis" · "AI Alarms". Button labels include "조회", "새로고침", "이전/다음" interspersed with English.  
**Industry expectation:** For a single-language deployment this is acceptable. For any export or international deployment, i18n scaffolding (e.g., gettext or Lingui) would be required. The current state makes automated UI testing with English-only tooling fragile.

---

### Gap 7: Background Loop Cancellation Not Fully Implemented

**Finding:** `BaseState` declares `_polling_task: Optional[asyncio.Task]` but never assigns it. Most infinite streaming loops (`DashboardRealtimeState.start_streaming`, `ForecastPlayerState.start_streaming`, `AlarmRTState.start_auto_refresh`) use a `while self.is_streaming:` pattern with a setter `stop_streaming()`, but there is no `asyncio.Task` handle stored, meaning task cancellation on page navigation may not reliably stop the background coroutine — creating zombie DB connections.  
**Evidence:** spec_02 §Background event accounting — "Cancellation pattern: most use `while self.is_streaming:` + setter — but no asyncio task tracking on most states. Risk of zombie loops on page navigation."  
**Industry expectation:** Long-running IoT applications must guarantee connection release on session disconnect to prevent DB connection pool exhaustion.

---

*End of spec_04_PRD.md*
