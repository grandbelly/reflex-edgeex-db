# Frontend Page Catalog — KSYS App
> Generated: 2026-05-28 | Source: ksys_app/pages/*.py + ksys_app/ksys_app.py

---

## Master Route Table

| Route URL | Registered? | Module File | Title | Core Function |
|-----------|-------------|-------------|-------|---------------|
| `/` | YES | `pages/dashboard.py` | Dashboard \| KSYS | Real-time sensor monitoring dashboard |
| `/alarms` | YES | `pages/alarms.py` | Alarms | Unified alarm dashboard (active + history, ISA-18.2) |
| `/alarms_rt` | YES | `pages/alarms_rt_simple.py` | 실시간 알람 상태 | Realtime alarm monitoring with sensor cards |
| `/alarms_rt_new` | YES | `pages/alarms_rt_new.py` | 실시간 알람 (개선) | Improved realtime alarm UI (alarm_item component) |
| `/alarms_hist` | YES | `pages/alarms_hist_simple.py` | 알람 이력 분석 | Alarm history query with pagination |
| `/alarms_hist_new` | YES | `pages/alarms_hist_new.py` | 알람 이력 (개선) | Improved alarm history with severity checkboxes |
| `/comm` | YES | `pages/communication.py` | (none set) | Communication success rate heatmap + daily trend |
| `/forecast` | YES | `pages/forecast_player.py` | 예측 플레이어 \| KSYS | Online ML prediction player with MAPE/NRMSE/accuracy |
| `/model-performance` | YES | `pages/model_performance.py` | 모델 성능 - KSYS | ML model performance comparison + deployment mgmt |
| `/scada-alarm-comparison` | YES | `pages/scada_alarm_comparison.py` | AI Alarms \| KSYS | Rule-based vs AI-based alarm comparison |
| `/scada-alarms` | YES | `pages/scada_alarm_viewer.py` | SCADA 알람 로그 | SCADA alarm log viewer with real-time streaming |
| `/training-wizard` | YES | `pages/training_wizard/__init__.py` | (none set) | 6-step ML model training wizard |
| `/trend` | YES | `pages/trend_enhanced_v2.py` | Trend Analysis | Sensor trend charts with brush sync + CSV export |
| `/viewer-tag` | YES | `pages/viewer_tag.py` | (none set) | Tag visibility management admin panel |
| `/design-system-demo` | **NOT IMPORTED** | `pages/design_system_demo.py` | Design System Demo \| KSYS | Component showcase (dev-only) |
| `/ai` | **NOT IMPORTED** | `pages/ai_insights.py` | AI 센서 인사이트 - KSys Dashboard | AI chat interface for sensor insights |

**Summary: 16 total page modules. 14 registered (imported in ksys_app.py). 2 dead/unregistered.**

---

## Dead / Unregistered Pages

### 1. `/ai` — `pages/ai_insights.py`
- Has `@rx.page("/ai", title="AI 센서 인사이트 - KSys Dashboard")` at line 568.
- Module is **NOT imported** in `ksys_app/ksys_app.py`. The decorator never executes.
- Contains a full chat interface (`AIState.send_message`, `AIState.load_initial_sensor_data`).
- AI features are environment-gated (`ENABLE_AI_FEATURES` env var) but the import gate is missing entirely.
- **Route `/ai` will return 404.**

### 2. `/design-system-demo` — `pages/design_system_demo.py`
- Has `@rx.page(route="/design-system-demo", ...)` at line 247.
- Module is **NOT imported** in `ksys_app/ksys_app.py`.
- Pure developer reference page (no real data). Intended as internal UI showcase.
- **Route `/design-system-demo` will return 404.**

---

## Per-Page Detail Catalog

---

### Page 1: Dashboard (`/`)
**File:** `pages/dashboard.py` (22 lines) + `views/dashboard_realtime_view.py`
**State(s):** `DashboardRealtimeState`, `SchedulerState`
**on_load:** `DashboardRealtimeState.start_streaming`, `SchedulerState.start_schedulers`

**Visible UI Elements:**
- Real-time sensor status table (columns: ID, 상태, 현재값, 범위, 초과량, 위험도, 판정시간, 액션)
- Status badges: NORMAL (green) / WARNING (amber) / CRITICAL (red)
- Risk bar visualization per sensor row
- Action buttons per row ("확인" / "조치")
- Sidebar navigation (via `shell` layout component)

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Click action button per row | State event (row-level action) |
| Page load triggers streaming | `DashboardRealtimeState.start_streaming` |
| Navigation sidebar links | Route navigation |

**Display Data:**
- Live sensor values with current/range/deviation
- Risk percentage bars
- Timestamp of last judgment per sensor
- Sensor count summary (total / normal / warning / critical)

**Test Scenarios:**
1. Open `/` — verify sensor table loads with data within 5s (start_streaming fires).
2. Verify NORMAL sensors show green badges; WARNING/CRITICAL show amber/red.
3. Click "조치" button on a CRITICAL sensor — verify UI responds.
4. Check browser console: no JS errors on initial load.
5. Wait 30s with page open — verify table values update (real-time streaming).

---

### Page 2: Alarms (`/alarms`)
**File:** `pages/alarms.py` (~465 lines)
**State(s):** `AlarmsState`, `DashboardRealtimeState`
**on_load:** `AlarmsState.initialize`, `DashboardRealtimeState.start_streaming`

**Visible UI Elements:**
- 4 stat cards: Total Sensors, Normal, Warning, Critical (from DashboardRealtimeState)
- View toggle: "Active Alarms" / "History" buttons
- **Active view:** Table (columns: ID, 상태, 현재값, 범위, 초과량, 위험도, 판정시간, 액션)
- **History view:** ISA-18.2 priority stats (4 cards: P1 Advisory, P2 Caution, P3 Warning, P4 Emergency)
  - Time range segmented control: 1h / 6h / 24h / 7d
  - "Show Acknowledged" toggle switch
  - Search/filter bar (`filter_bar` component)
  - Info bar: filtered count + last update
  - Table (columns: 상태, 시간, 센서, ISA Priority, 시나리오, 값, 메시지, 액션)
  - Pagination component
- "Refresh" button (top right)
- Error callout (shown on error)
- Loading spinner (during data fetch)

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Click "Active Alarms" tab | `AlarmsState.set_view_mode("active")` |
| Click "History" tab | `AlarmsState.set_view_mode("history")` |
| Click "Refresh" | `AlarmsState.refresh_data` |
| Select time range (1h/6h/24h/7d) | `AlarmsState.set_hours_filter` |
| Toggle "Show Acknowledged" | `AlarmsState.toggle_show_acknowledged` |
| Type in search box | `AlarmsState.set_search_query` |
| Select severity filter | `AlarmsState.set_severity_filter` |
| Select status filter | `AlarmsState.set_status_filter` |
| Click "Acknowledge" on an alarm | `AlarmsState.acknowledge_alarm(event_id)` |
| Click Previous/Next page | `AlarmsState.prev_page` / `AlarmsState.next_page` |

**Display Data:**
- ISA-18.2 alarm priorities (P1–P4) with color coding
- Scenario type badge: RULE_BASE (blue) / AI_BASE (purple)
- Real-time sensor status from dashboard state

**Test Scenarios:**
1. Load `/alarms` in Active view — verify sensor table appears with status badges.
2. Switch to History view — verify ISA-18.2 priority cards appear and alarm list loads.
3. Change time range to 7d — verify alarm count updates.
4. Search for a known tag name — verify list filters correctly.
5. Click "Acknowledge" on an unacknowledged alarm — verify badge changes to "확인완료".

---

### Page 3: Realtime Alarms Simple (`/alarms_rt`)
**File:** `pages/alarms_rt_simple.py` (~400 lines)
**State(s):** `AlarmRTState` (aliased as `A`)
**on_load:** `A.load_all_data`

**Visible UI Elements:**
- 4 sensor status stat cards (Total/Normal/Warning/Critical sensors)
- Sensor detail grid (responsive 2→6 column card grid for all sensors)
- 6 alarm stat cards (Total/Critical/Warning/Info alarms + Unacked/Acked)
- Filter bar (static render, no state binding — see note below)
- Action bar (showing count)
- Alarm list (cards per alarm with current value, threshold, scenario badge)
- "Acknowledge" button per alarm
- "Load More" button (static, no handler)
- Pagination count display

**Note on filter_bar:** The filter_bar is rendered with hardcoded `search_value=""`, `severity_filter="all"` — filter inputs are NOT wired to state. Filtering does not work.

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Click "새로고침" | `A.load_all_data` |
| Click "Acknowledge" per alarm | `A.acknowledge_alarm(tag_name)` |

**Display Data:**
- Per-sensor: tag_name, status, description, current value, unit, range, timestamp
- Per-alarm: status badge, tag, current_value, threshold range, scenario type, last alarm time

**Test Scenarios:**
1. Load `/alarms_rt` — verify sensor cards grid loads (responsive at narrow viewport).
2. Verify alarm cards show correct threshold ranges.
3. Click Acknowledge on a WARNING alarm — verify badge updates.
4. Click Refresh — verify data refreshes.
5. Check "Load More" button — expect it does nothing (unimplemented, bug).

---

### Page 4: Realtime Alarms New (`/alarms_rt_new`)
**File:** `pages/alarms_rt_new.py` (~180 lines)
**State(s):** `AlarmRTState` (aliased as `A`)
**on_load:** `A.on_load` (via `on_mount` in shell call)

**Visible UI Elements:**
- 6 stat cards (Total/Critical/Warning/Info/Unacked/Acked)
- Filter bar (same static binding issue as /alarms_rt)
- Action bar
- Alarm list using `alarm_item` component (from `components/alarms/alarm_item.py`)
- "Next" pagination button (static, no handler)
- LIVE indicator badge + Refresh button

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Click "Refresh" | `A.refresh_realtime` |

**Test Scenarios:**
1. Load `/alarms_rt_new` — verify alarm_item component renders correctly vs /alarms_rt.
2. Compare alarm_item styling with /alarms_rt cards.
3. Verify LIVE indicator badge is visible.
4. Click Refresh — verify list updates.
5. Note: "Next" pagination button is wired to no handler — document as bug.

---

### Page 5: Alarm History Simple (`/alarms_hist`)
**File:** `pages/alarms_hist_simple.py` (~286 lines)
**State(s):** `AlarmHistState`
**on_load:** `AlarmHistState.on_load` (via `on_mount`)

**Visible UI Elements:**
- Page header with datetime range pickers (start/end, type=datetime-local)
- 조회 button
- 4 stat cards: 총 알람, 최다 센서, 평균 레벨, 해결율
- Alarm history list (cards): shows acknowledged status, triggered_at, tag_name, level badge, scenario, value, message, resolved status
- Pagination: 이전/다음 buttons + page info

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Set start datetime | `AlarmHistState.set_start_date` |
| Set end datetime | `AlarmHistState.set_end_date` |
| Click 조회 | `AlarmHistState.fetch_history` |
| Click 이전 | `AlarmHistState.prev_page` |
| Click 다음 | `AlarmHistState.next_page` |

**Display Data:**
- Alarm cards with acknowledged/unacknowledged status (visual priority)
- Scenario ID badges: AI_BASE (purple) / DYNAMIC_RULE (blue) / other (gray)
- Resolved / in-progress badge

**Test Scenarios:**
1. Load `/alarms_hist` — verify page renders with empty state or last query.
2. Set start/end date range covering today and click 조회 — verify alarms list populates.
3. Navigate pages (이전/다음) — verify page counter updates.
4. Set date range with no data — verify empty state shown.
5. Check stat cards update after 조회.

---

### Page 6: Alarm History New (`/alarms_hist_new`)
**File:** `pages/alarms_hist_new.py` (~285 lines)
**State(s):** `AlarmHistState`
**on_load:** `AlarmHistState.on_load` (via `on_mount`)

**Visible UI Elements:**
- Date range quick-select buttons: 오늘 / 어제 / 1주일 / 1개월 (segmented)
- Severity checkboxes: Critical / Warning / Info
- 조회 button
- 4 stat cards: 총 알람, Critical, Warning, Info (colored)
- Alarm history table (columns: 발생시간, 종료시간, 태그, 심각도, 메시지, 지속시간)
- Pagination (이전/다음 + page info)
- Empty state illustration

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Click 오늘/어제/1주일/1개월 | `AlarmHistState.set_date_range(key)` |
| Toggle Critical checkbox | `AlarmHistState.toggle_critical` |
| Toggle Warning checkbox | `AlarmHistState.toggle_warning` |
| Toggle Info checkbox | `AlarmHistState.toggle_info` |
| Click 조회 | `AlarmHistState.search_alarms` |
| Click 이전/다음 | `AlarmHistState.prev_page` / `AlarmHistState.next_page` |

**Test Scenarios:**
1. Load `/alarms_hist_new` — verify date quick-select buttons render.
2. Click "오늘" — verify date range updates and alarms load.
3. Uncheck "Critical" — click 조회 — verify critical alarms are hidden.
4. Click "1개월" — verify large dataset loads with pagination.
5. Navigate through multiple pages — verify content changes.

---

### Page 7: Communication (`/comm`)
**File:** `pages/communication.py` (~200+ lines)
**State(s):** `CommunicationState`
**on_load:** `CommunicationState.initialize`

**Visible UI Elements:**
- Header: "통신 성공률" + Real-time badge
- Controls card: sensor selector dropdown + period segmented control (3일/7일/14일/30일)
- Stat cards (success rate metrics)
- Daily success rate trend area chart (with 95% reference line)
- Wrapped grid heatmap (hourly data collection success per day)

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Select sensor | `CommunicationState.set_selected_tag` |
| Select period (3/7/14/30일) | `CommunicationState.set_selected_days_str` |

**Display Data:**
- Daily success rate as area chart (0–100%, 95% threshold line)
- Hourly heatmap grid showing data collection completeness per sensor

**Test Scenarios:**
1. Load `/comm` — verify heatmap renders (if data exists).
2. Change sensor selection — verify heatmap and chart update.
3. Switch period to 30일 — verify chart extends.
4. Verify 95% reference line appears on area chart.
5. Check that missing data hours show clearly in heatmap (low-color cells).

---

### Page 8: Forecast Player (`/forecast`)
**File:** `pages/forecast_player.py` (~958 lines) — most complex page
**State(s):** `ForecastPlayerState` (aliased as `FPS`)
**on_load:** `FPS.load_deployed_models`, `FPS.start_countdown_monitor`

**Visible UI Elements:**
- Page header with subtitle (interval info)
- 3 metric cards: MAPE (green gradient), NRMSE (purple gradient), 예측 정확도 (pink gradient)
- Formula display section: RMSE → Mean → CV-RMSE → Accuracy step cards
- Terminology glossary (collapsible info box)
- Model selector dropdown (deployed models list)
- "데이터 새로고침" button
- System info panel (센서명, 예측 횟수, 갱신 주기, 모델, 데이터 윈도우, 예측 호라이즌)
- Update status panel (T0 기준 시간, 마지막 업데이트, 예측 스케줄러 status, 다음 예측 countdown)
- Main chart: ComposedChart with past/future zones, T0 reference line, actual + predicted + CI bands
  - Y-axis scale toggle: "0 기준" ↔ "자동 스케일"
- Data table: horizontal (rows = metrics, columns = time points) with scroll
  - Rows: 실제 시간, 실측값, 예측값, 절대오차, 상대오차(%), MAPE, 상태
  - Colored by past (blue) / present (yellow) / future (green)
- Empty state with "스트리밍 시작" button

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Select model from dropdown | `FPS.select_model` |
| Click 데이터 새로고침 | `FPS.load_predictions` |
| Toggle Y-axis scale | `FPS.toggle_y_axis_scale` |
| Click 스트리밍 시작 (empty state) | `FPS.start_streaming` |
| Page load | `FPS.load_deployed_models`, `FPS.start_countdown_monitor` |

**Display Data:**
- Online ML predictions vs actual sensor values
- MAPE / NRMSE / CV-RMSE accuracy metrics
- Rolling window time series with confidence intervals
- Scheduler status and next-prediction countdown

**Test Scenarios:**
1. Load `/forecast` — verify deployed models dropdown populates.
2. Select a model — verify metric cards (MAPE/NRMSE/accuracy) populate.
3. Verify chart renders with past zone (blue) and future zone (orange) + T0 red line.
4. Toggle Y-axis scale — verify chart re-renders with correct domain.
5. Scroll horizontal data table — verify all time columns visible with correct color coding.

---

### Page 9: Model Performance (`/model-performance`)
**File:** `pages/model_performance.py` (~262 lines)
**State(s):** `ModelPerformanceState` (aliased as `M`)
**on_load:** `M.on_mount`

**Visible UI Elements:**
- Page header: "모델 성능 모니터링"
- Error callout (on error)
- Control panel: sensor selector + Refresh button + last-update timestamp badge
- Section 1 — Algorithm Comparison chart (Prophet / Auto-ARIMA / XGBoost)
- Best Algorithm card highlight
- Section 2 — Deployed Model Info card
- Section 3 — Saved Models Table with "배포" (Deploy) buttons
- Section 4 — ML Pipeline comparison cards (Top 3 + deployed, grid layout)

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Select sensor | `M.set_selected_sensor` |
| Click 새로고침 | `M.refresh_data` |
| Click 배포 (deploy) button per model | (deploy action — in `saved_models_table` component) |

**Display Data:**
- Algorithm validation MAPE comparison (bar chart)
- Best algorithm highlighted card
- Currently deployed model (name, sensor, accuracy, training date)
- All saved models in table (model_id, name, tag, MAPE, training params)
- Pipeline configuration details per top-3 models

**Test Scenarios:**
1. Load `/model-performance` — verify sensor dropdown loads available sensors.
2. Select a sensor — verify algorithm comparison chart updates.
3. Verify "Best Algorithm" card shows the lowest-MAPE algorithm.
4. Find a model in Saved Models table and click 배포 — verify deployment message appears.
5. Check ML Pipeline section shows up to 3 pipeline cards side by side.

---

### Page 10: SCADA Alarm Comparison (`/scada-alarm-comparison`)
**File:** `pages/scada_alarm_comparison.py` (~400+ lines)
**State(s):** `ScadaAlarmComparisonState`
**on_load:** (check registration only)

**Visible UI Elements:**
- Page header: "AI Alarms Comparison"
- Stat cards for rule-based vs AI-based counts
- Dual alarm tables: Rule-based alarms | AI-based alarms
- Severity badges (CAUTION/INFO/WARNING/ERROR/CRITICAL)
- Method badges (Rule-based blue / AI-based purple)

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| (check state for filter/refresh events) | `ScadaAlarmComparisonState.*` |

**Test Scenarios:**
1. Load `/scada-alarm-comparison` — verify both tables render.
2. Verify Rule-based badges show blue, AI-based show purple.
3. Compare alarm counts in stat cards vs table rows.
4. Check that alarms with same timestamp but different methods both appear.
5. Verify page renders without JS errors.

---

### Page 11: SCADA Alarm Viewer (`/scada-alarms`)
**File:** `pages/scada_alarm_viewer.py`
**State(s):** `ScadaAlarmState`
**on_load:** (no explicit on_load; streaming initiated via button)

**Visible UI Elements:**
- Heading: "SCADA 알람 실시간 로그" + total count
- Refresh button
- Start/Stop streaming toggle button (plays/pauses real-time)
- Severity filter dropdown (전체/긴급/위험/경고/주의/정보)
- Tag name search input
- Last update timestamp
- Alarm log table

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Click 새로고침 | `ScadaAlarmState.load_alarm_logs` |
| Click 실시간 시작 / 정지 | `ScadaAlarmState.toggle_streaming` |
| Select severity filter | `ScadaAlarmState.set_severity_filter` |
| Type tag filter | `ScadaAlarmState.set_tag_filter` |

**Test Scenarios:**
1. Load `/scada-alarms` — verify alarm table shows historical data.
2. Click 실시간 시작 — verify button changes to 정지 and new rows appear.
3. Filter by 긴급 severity — verify only high-severity rows remain.
4. Type a tag name in search — verify rows filter.
5. Click 정지 — verify streaming halts.

---

### Page 12: Training Wizard (`/training-wizard`)
**File:** `pages/training_wizard/__init__.py` (93 lines) + 6 step files + results submodule
**State(s):** `TrainingWizardState`
**on_load:** `TrainingWizardState.initialize_wizard`

**Visible UI Elements:**
- Wizard header with progress bar (step N of 6)
- Error display callout
- Step content area (conditional per wizard_step 1–6):
  - Step 1: Sensor selection (step_1_sensor.py)
  - Step 2: Model algorithm selection (step_2_model.py)
  - Step 3: Feature configuration (step_3_features.py)
  - Step 4: Training parameter tuning (step_4_params.py)
  - Step 5: Execute training (step_5_training.py)
  - Step 6: View results + model diagnostics (step_6_results.py)
- Navigation: Back / Next / Train buttons

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Select sensor (Step 1) | `TrainingWizardState.*` |
| Select model algorithm (Step 2) | `TrainingWizardState.*` |
| Configure features (Step 3) | `TrainingWizardState.*` |
| Set training params (Step 4) | `TrainingWizardState.*` |
| Start training (Step 5) | `TrainingWizardState.*` (training execution) |
| View results (Step 6) | Display only, deploy action |
| Next / Back navigation | `TrainingWizardState.*` |

**Display Data (Step 6):**
- Performance summary (MAPE, R², accuracy)
- Fold results table
- Validation charts
- Model diagnostics
- Residuals diagnostics
- Algorithm comparison (data_summary, evaluation_metrics, model_selection_info)

**Test Scenarios:**
1. Load `/training-wizard` — verify Step 1 (sensor selection) renders.
2. Select a sensor and click Next — verify step advances to Step 2.
3. Navigate all 6 steps forward/backward without error.
4. Complete all steps and submit training (Step 5) — verify loading state appears.
5. After training completes, navigate to Step 6 — verify result charts render.

---

### Page 13: Trend Analysis (`/trend`)
**File:** `pages/trend_enhanced_v2.py` (~849 lines)
**State(s):** `TrendState` (aliased as `T`)
**on_load:** `T.load` (also on_mount)

**Visible UI Elements:**
- Control card:
  - Tag selector dropdown
  - Aggregation unit selector: 1m / 10m / 1h / 1d
  - Time range selector dropdown
  - Current selection summary badges
- Chart card:
  - Chart type: Area / Line / Bar (segmented)
  - Y-axis: Auto / Fixed toggle button
  - Data selector: Average / Minimum / Maximum / First / Last (segmented)
  - Info callout (brush usage tip)
  - Top chart (Area/Line/Bar — user selected)
  - Bottom chart: ComposedChart with avg/max/min + Brush range selector
  - Two charts sync via `sync_id="trend"`
- Data table card:
  - Columns: No. / Tag / Timestamp / Average / Min / Max / Last / First / Count
  - Missing data rows highlighted in red
  - CSV export dropdown (전체 / 현재 페이지)
  - Pagination (page size selector: 10/20/50/100 + prev/next)
  - Data completeness badge + missing count badge

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Select tag | `T.set_tag_select` |
| Select aggregation (1m/10m/1h/1d) | `T.set_aggregation_view` |
| Select time range | `T.set_time_range` |
| Click 새로고침 | `T.load` |
| Switch chart mode | `T.set_chart_mode` |
| Toggle Y-axis auto/fixed | `T.toggle_auto_scale` |
| Select data type (avg/min/max/first/last) | `T.set_trend_selected` |
| Drag Brush on bottom chart | (recharts brush — client-side, syncs top chart) |
| Export CSV (all) | `T.export_csv_all` |
| Export CSV (page) | `T.export_csv_page` |
| Change page size | `T.set_page_size` |
| Click 이전/다음 page | `T.prev_page` / `T.next_page` |

**Test Scenarios:**
1. Load `/trend` — verify tag dropdown populated.
2. Select a tag + 1h aggregation + last 24h — verify charts render.
3. Switch chart from Area to Line — verify top chart changes.
4. Drag brush on bottom chart — verify top chart zooms.
5. Click "CSV 내보내기 > 전체 데이터" — verify file download triggers.

---

### Page 14: Viewer Tag (`/viewer-tag`)
**File:** `pages/viewer_tag.py`
**State(s):** `ViewerTagState`
**on_load:** (no explicit on_load; loaded via `ViewerTagState.load_tags` on button)

**Visible UI Elements:**
- Heading "Viewer Tags"
- "Add Tag" button (green)
- "Refresh" button
- Error callout / Success callout (conditional)
- Tags table (columns: Order / Tag Name / Dashboard / Alarm / Trend / Model / Actions)
  - Display Order: editable number input per row
  - Dashboard/Alarm/Trend/Model: toggle switches per row
  - Actions: delete button per row
- Add Tag dialog:
  - Tag name text input
  - Available tags list (tags not yet configured, with + buttons)
  - Confirm/Cancel buttons

**User-Actionable Features:**
| Action | Event Handler |
|--------|--------------|
| Click "Refresh" | `ViewerTagState.load_tags` |
| Click "Add Tag" | `ViewerTagState.open_add_dialog` |
| Edit display_order input | `ViewerTagState.update_order(tag_name, value)` |
| Toggle Dashboard switch | `ViewerTagState.toggle_dashboard(tag_name)` |
| Toggle Alarm switch | `ViewerTagState.toggle_alarm(tag_name)` |
| Toggle Trend switch | `ViewerTagState.toggle_trend(tag_name)` |
| Toggle Model switch | `ViewerTagState.toggle_model(tag_name)` |
| Click + in dialog list | `ViewerTagState.set_add_tag_name(tag_name)` |
| Confirm Add Tag | `ViewerTagState.add_tag` (inferred) |
| Delete tag | (delete action in row) |

**Display Data:**
- Complete list of configured viewer tags
- Visibility flags per tag per screen (dashboard/alarm/trend/model)

**Test Scenarios:**
1. Load `/viewer-tag` — verify tags table loads.
2. Toggle Dashboard switch for a tag — verify state updates (switch changes).
3. Change display_order for a tag (blur input) — verify order persists on refresh.
4. Click "Add Tag" — verify dialog opens with available tags.
5. Delete a tag — verify it disappears from the table and a success callout appears.

---

## Component Library

### components/layout.py
- **`shell(content, active_route)`** — Top-level page shell with sidebar navigation. Used by ALL registered pages.

### components/alarms/
| Component | File | Purpose | Used in |
|-----------|------|---------|---------|
| `stat_card` | `stat_card.py` | Colored stat tile (title/value/icon/color) | alarms.py, alarms_rt_simple.py, alarms_rt_new.py |
| `filter_bar` | `filter_bar.py` | Search + severity + status filter row | alarms.py, alarms_rt_simple.py, alarms_rt_new.py |
| `pagination` | `pagination.py` | Prev/Next pagination with page info | alarms.py |
| `alarm_item` | `alarm_item.py` | Individual alarm card component | alarms_rt_new.py |
| `live_indicator` | (in `__init__.py`) | LIVE badge with last update | alarms_rt_simple.py, alarms_rt_new.py |
| `action_bar` | (in `__init__.py`) | Shown/selected count bar | alarms_rt_simple.py, alarms_rt_new.py |

### components/cards/
| Component | File | Purpose | Used in |
|-----------|------|---------|---------|
| `stat_card` | `stat_card.py` | Generic stat card | alarms.py |
| `kpi_card` | `kpi_card.py` | KPI metric card | (dashboard, kpi_tiles) |

### components/charts/
| Component | File | Purpose | Used in |
|-----------|------|---------|---------|
| `mini_chart` | `mini_chart.py` | Compact sparkline chart | (dashboard tiles) |

### components/trends/
Modular trend sub-system with sub-packages: `cards/`, `charts/`, `feedback/`, `inputs/`, `layout/`
| Component | File | Purpose |
|-----------|------|---------|
| `HierarchicalTagSelector` | `inputs/hierarchical_tag_selector.py` | Tag picker with hierarchy |
| `ChartModeSelector` | `inputs/chart_mode_selector.py` | Area/Line/Bar toggle |
| `TagSelector` | `inputs/tag_selector.py` | Tag dropdown |
| `TimeRangeSelector` | `inputs/time_range_selector.py` | Time range picker |
| `TrendChart` | `charts/trend_chart.py` | Main trend chart |
| `ChartContainer` | `charts/chart_container.py` | Chart wrapper with loading |
| `EmptyState` | `feedback/empty_state.py` | No-data placeholder |
| `LoadingState` | `feedback/loading_state.py` | Loading spinner |
| `PageHeader` | `layout/page_header.py` | Trend page header |
| `SectionContainer` | `layout/section_container.py` | Section wrapper |

### Standalone Components
| Component | File | Purpose | Used in |
|-----------|------|---------|---------|
| `page_header` | `page_header.py` | Reusable page header w/ title/icon/actions | alarms_rt_simple, alarms_hist_simple, forecast_player, model_performance |
| `forecast_chart` | `forecast_chart.py` | Recharts forecast line chart | (forecast pages) |
| `forecast_chart_plotly` | `forecast_chart_plotly.py` | Plotly version of forecast chart | (backup/alternate) |
| `algorithm_comparison_chart` | `algorithm_comparison_chart.py` | Bar chart comparing algorithm MAPE | model_performance |
| `performance_charts` | `performance_charts.py` | `model_comparison_chart`, `saved_models_table`, `deployed_model_info_card` | model_performance |
| `pipeline_detail_card` | `pipeline_detail_card.py` | ML pipeline config card | model_performance |
| `wrapped_heatmap` | `wrapped_heatmap.py` | Hourly grid heatmap | communication |
| `gauge` | `gauge.py` | Circular gauge widget | (dashboard KPIs) |
| `realtime_chart` | `realtime_chart.py` | Live-updating chart | (dashboard) |
| `sparkline_chart` | `sparkline_chart.py` | Tiny trend line | (tiles) |
| `sensor_card_enhanced` | `sensor_card_enhanced.py` | Enhanced sensor card | (dashboard) |
| `design_system` | `design_system.py` | `DesignSystem` class — heading/card/metric_card etc. | design_system_demo.py |
| `layout_v2` | `layout_v2.py` | Alternate layout shell | (unused or alternate) |
| `status_badge` | `status_badge.py` | Generic status badge | (scattered) |
| `time_selector` | `time_selector.py` | Time range input | (older pages) |
| `kpi_tiles` | `kpi_tiles.py` | KPI tile grid | (dashboard) |
| `trend_enhanced` | `trend_enhanced.py` | Old trend component (superseded by v2) | (deprecated) |
| `saved_data_display` | `saved_data_display.py` | Display saved model results | (model perf) |
| `stock_chart` | `stock_chart.py` | Candlestick/OHLC style chart | (unused or experimental) |
| `features_table` | `features_table.py` | Feature importance table | (training wizard) |
| `indicators_table` | `indicators_table.py` | Technical indicator display | (deprecated, removed from views) |
| `training_charts` | `training_charts.py` | Training result charts | (training wizard) |
| `ai_visualizations` | `ai_visualizations.py` | AI insight visualization components | (ai_insights — dead page) |
| `forecast_panel` | `forecast_panel.py` | Forecast summary panel | (forecast player) |

---

## Known Issues / Surprises

### Issue 1: `/ai` Page — Dead Route (NOT REGISTERED)
- `pages/ai_insights.py` has `@rx.page("/ai", ...)` but is never imported in `ksys_app.py`.
- The `ENABLE_AI_FEATURES` env flag exists but the import guard that should conditionally import the page is missing.
- All AI service code (`ai_service.py`, `ai_state.py`) and `ai_visualizations.py` component exist but are unreachable.
- **Impact:** Any sidebar link pointing to `/ai` will 404.

### Issue 2: Filter Bar Not Wired in `/alarms_rt` and `/alarms_rt_new`
- Both pages call `filter_bar(search_value="", severity_filter="all", status_filter="all")` with hardcoded literals.
- The filter_bar component likely has `on_search`, `on_severity_change`, `on_status_change` props that are not being passed.
- **Impact:** Search and severity/status filtering are completely non-functional on both realtime alarm pages.

### Issue 3: "Load More" / "Next" Pagination Buttons Are Dead
- `/alarms_rt_simple.py` line ~382: "Load More" button has no `on_click`.
- `/alarms_rt_new.py` line ~160: "Next" button has no `on_click`.
- **Impact:** Pagination on both realtime alarm pages is broken — users can never scroll past the first page.

### Issue 4: Duplicate Pages for Same Feature
- `/alarms_rt` (simple) and `/alarms_rt_new` (new) both exist, registered, backed by the same `AlarmRTState`.
- `/alarms_hist` (simple) and `/alarms_hist_new` (new) both exist, registered, backed by the same `AlarmHistState`.
- No redirect or canonical URL disambiguation. Users may encounter either version depending on navigation.
- The "simple" variants predate the "new" variants; it is unclear which is the intended production path.

### Issue 5: `design_system_demo` Not Imported
- Pure developer showcase page. Not harmful but means `/design-system-demo` 404s.
- If a developer wants to reference the design system visually, they must add the import.

---

## Appendix: Lines of Code by Page (Complexity Proxy)

| Page | Module | Approx LoC | Complexity |
|------|--------|-----------|------------|
| `/forecast` | forecast_player.py | ~958 | Very High |
| `/trend` | trend_enhanced_v2.py | ~849 | Very High |
| `/alarms` | alarms.py | ~465 | High |
| `/alarms_rt` | alarms_rt_simple.py | ~400 | High |
| `/scada-alarm-comparison` | scada_alarm_comparison.py | ~400+ | High |
| `/training-wizard` | wizard/ (18 files) | ~1500+ total | Very High |
| `/model-performance` | model_performance.py | ~262 | Medium |
| `/alarms_rt_new` | alarms_rt_new.py | ~180 | Medium |
| `/alarms_hist_new` | alarms_hist_new.py | ~285 | Medium |
| `/alarms_hist` | alarms_hist_simple.py | ~286 | Medium |
| `/comm` | communication.py | ~200+ | Medium |
| `/viewer-tag` | viewer_tag.py | ~250+ | Medium |
| `/scada-alarms` | scada_alarm_viewer.py | ~200+ | Low-Med |
| `/` | dashboard.py | ~22 (view in views/) | High (view) |
