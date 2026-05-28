# KSys IoT — Master Test Catalog

**Generated:** 2026-05-28 | **Author:** QA Strategist (reverse-engineered) | **Source:** spec_01 + spec_02 + spec_03 + audit_consolidated_2026-05-21 + playwright_test_2026-05-28 + trust_audit_2026-05-28

**Total test cases proposed: 124**

## Section 1 — Test Pyramid

This is a Reflex (Python SSR + React SPA) app on a Raspberry Pi edge deployment with 14 live routes, 2 dead routes, 201 `@rx.event` handlers (112 background), 6 schedulers, no authentication, Cloudflare tunnel public exposure. **HTTP 200 from curl does NOT prove a page works** — Reflex SPA serves shell HTML to all routes; client-side router resolves actual content (confirmed in playwright_test_2026-05-28).

| Tier | Name | When | Target Duration | Cases | Purpose |
|------|------|------|----------------|-------|---------|
| Tier-1 | Smoke | Every PR | < 60s | 10 | Build not broken |
| Tier-2 | Functional | Nightly | 8-12 min | 52 | Main user flows |
| Tier-3 | Regression | Weekly/pre-deploy | 45-60 min | 50 | Full feature + data-flow |
| Tier-4 | Performance | Monthly (RPI) | 2-4 hrs | 12 | RPI baseline measurements |

## Section 2 — Test Method Matrix

| Test Type | Tool | Notes |
|-----------|------|-------|
| UI smoke / page load | Playwright `browser_navigate` + title check | Must check title != "404 - Not Found" |
| State event handler (read) | Playwright button click + snapshot | Exercises WS round-trip |
| State event handler (DB write) | Playwright action + psql verify | Click in browser, psql confirm mutation |
| Service / DB write isolation | pytest + real test DB (not mocked) | Mocks masked production failures historically |
| Scheduler correctness | docker logs grep + DB row count delta | In-process schedulers; logs confirm execution |
| SQL injection | Playwright typed input with payload + assert no leak | Audit H-02 found interpolation in dynamic_rag_engine.py |
| Long-running stream / leak | docker stats + pg_stat_activity over N min | Verify no zombie tasks/connections |
| Cross-RPI deploy | `bootstrap_rpi.sh` + `restore_db.sh` on clean machine | Manual quarterly |
| Reflex backend health | `curl /_ping` | Part of smoke |
| DB pool health | `docker exec psql -c "SELECT 1"` | Part of smoke |
| Continuous aggregate refresh | psql count on `influx_agg_1m WHERE bucket > NOW()-2h` | Part of scheduler checks |

## Section 3 — Test Case Matrix by Domain

### Domain 1: Alarm (10 cases)

| TC-ID | Description | Priority | Method |
|-------|-------------|----------|--------|
| TC-ALARM-01 | `/alarms` loads — active view; stat cards show counts | P0 | Playwright |
| TC-ALARM-02 | Switch to History tab; ISA-18.2 P1-P4 priority cards render | P0 | Playwright |
| TC-ALARM-03 | Acknowledge single alarm; psql confirms `acknowledged=true` | P0 | Playwright + psql |
| TC-ALARM-04 | Bulk acknowledge N alarms; psql count increases by N | P1 | Playwright + psql |
| TC-ALARM-05 | Time range filter 1h/6h/24h/7d returns different counts | P1 | Playwright |
| TC-ALARM-06 | Search by tag name filters correctly | P1 | Playwright |
| TC-ALARM-07 | `/alarms_hist_new` severity checkbox filter (Critical off → no Critical rows) | P1 | Playwright |
| TC-ALARM-08 | Acknowledge idempotency — second call no-ops | P1 | pytest + DB |
| TC-ALARM-09 | `/alarms_rt` sensor cards grid renders | P1 | Playwright |
| TC-ALARM-10 | cleanup_old_alarms deletes old acknowledged; newer untouched | P2 | pytest + DB |

### Domain 2: Forecast (10 cases)

| TC-ID | Description | Priority | Method |
|-------|-------------|----------|--------|
| TC-FCAST-01 | `/forecast` loads; deployed model dropdown populated | P0 | Playwright |
| TC-FCAST-02 | Select model populates MAPE/NRMSE/accuracy metric cards | P0 | Playwright |
| TC-FCAST-03 | Chart renders past (blue) / future (orange) / T0 (red) zones | P1 | Playwright screenshot |
| TC-FCAST-04 | Y-axis "자동 스케일" toggle changes domain | P1 | Playwright |
| TC-FCAST-05 | ForecastScheduler runs every 10min; predictions table grows | P0 | docker logs + psql |
| TC-FCAST-06 | ActualValueUpdater backfills past actual_value | P1 | psql |
| TC-FCAST-07 | trigger_forecast_now manual button works | P1 | Playwright + psql |
| TC-FCAST-08 | Deploy model sets `is_deployed=true` | P1 | Playwright + psql |
| TC-FCAST-09 | Undeploy removes from `/forecast` dropdown | P1 | Playwright + psql |
| TC-FCAST-10 | forecast_player_cache populated after scheduler cycle | P1 | psql |

### Domain 3: Training (10 cases)

| TC-ID | Description | Priority | Method |
|-------|-------------|----------|--------|
| TC-TRAIN-01 | `/training-wizard` Step 1 loads; progress bar shows 1 of 6 | P0 | Playwright |
| TC-TRAIN-02 | Forward navigation Step 1 → 2 | P1 | Playwright |
| TC-TRAIN-03 | Backward navigation preserves form state | P1 | Playwright |
| TC-TRAIN-04 | Validation gate — cannot skip required step | P1 | Playwright |
| TC-TRAIN-05 | Walk-forward feasibility check returns shortage error for too-short window | P1 | pytest unit |
| TC-TRAIN-06 | create_feature_config writes to DB | P1 | pytest + DB |
| TC-TRAIN-07 | start_training completes; Step 6 reachable | P2 | Playwright (slow) |
| TC-TRAIN-08 | save_model — model_registry row with `model_pickle IS NOT NULL` | P1 | Playwright + psql |
| TC-TRAIN-09 | Step 6 charts (MAPE, R², fold) render | P2 | Playwright |
| TC-TRAIN-10 | Container restart — wizard requires re-train (cache in-memory) | P2 | Manual |

### Domain 4: Sensor / Viewer-Tag (10 cases)

| TC-ID | Description | Priority | Method |
|-------|-------------|----------|--------|
| TC-SENSOR-01 | `/viewer-tag` loads; tags table populates | P0 | Playwright |
| TC-SENSOR-02 | toggle_dashboard persists to `viewer_tag` table | P1 | Playwright + psql |
| TC-SENSOR-03 | toggle propagates to `influx_latest` view filter | P1 | psql |
| TC-SENSOR-04 | add_tag inserts row; appears in table | P1 | Playwright + psql |
| TC-SENSOR-05 | delete_tag removes from `viewer_tag` | P1 | Playwright + psql |
| TC-SENSOR-06 | update_order persists display_order changes | P2 | Playwright + psql |
| TC-SENSOR-07 | show_all_dashboard bulk update | P2 | Playwright + psql |
| TC-SENSOR-08 | save_sensor_info updates `influx_qc_rule`; AlarmMonitor picks up next cycle | P1 | Playwright + psql |
| TC-SENSOR-09 | Virtual tag values appear in `influx_hist` over 2 min | P2 | psql |
| TC-SENSOR-10 | `/comm` heatmap renders cells; area chart visible | P1 | Playwright |

### Domain 5: Dashboard (8 cases)

| TC-ID | Description | Priority | Method |
|-------|-------------|----------|--------|
| TC-DASH-01 | `/` loads — sensor table with status badges | P0 | Playwright |
| TC-DASH-02 | start_streaming fires WS message within 5s | P0 | Playwright |
| TC-DASH-03 | Real-time update — at least 1 sensor value changes over 35s | P1 | Playwright timed |
| TC-DASH-04 | Status badge color coding (CRITICAL=red, WARNING=amber, NORMAL=green) | P1 | Playwright screenshot |
| TC-DASH-05 | No zombie tasks on navigation — `pg_stat_activity` stable | P1 | psql monitor |
| TC-DASH-06 | SCADA alarm viewer `실시간 시작` streams new rows within 10s | P1 | Playwright |
| TC-DASH-07 | SCADA alarm severity filter narrows results | P1 | Playwright |
| TC-DASH-08 | DB unavailable — error callout, no unhandled exception | P2 | Manual |

### Domain 6: Trend (10 cases)

| TC-ID | Description | Priority | Method |
|-------|-------------|----------|--------|
| TC-TREND-01 | `/trend` loads; tag dropdown populated; title = "Trend Analysis" | P0 | Playwright |
| TC-TREND-02 | Tag + 1h agg + 24h range → charts + table render | P1 | Playwright |
| TC-TREND-03 | Chart type switch Area → Line | P1 | Playwright screenshot |
| TC-TREND-04 | CSV export — all data; valid CSV file | P1 | Playwright (download) |
| TC-TREND-05 | CSV export — current page; rows match page_size | P1 | Playwright |
| TC-TREND-06 | Pagination next page works | P1 | Playwright |
| TC-TREND-07 | Page size change recalculates pagination | P2 | Playwright |
| TC-TREND-08 | Missing data rows highlighted | P2 | Playwright screenshot |
| TC-TREND-09 | Auto-refresh — no leak after 5 cycles | P2 | psql monitor |
| TC-TREND-10 | Y-axis fixed vs auto toggle | P2 | Playwright |

### Domain 7: Data Integration (10 cases)

| TC-ID | Description | Priority | Method |
|-------|-------------|----------|--------|
| TC-INT-01 | ForecastScheduler heartbeat in docker logs after 12min | P0 | docker logs |
| TC-INT-02 | AlarmMonitor heartbeat in docker logs after 15s | P0 | docker logs |
| TC-INT-03 | SchedulerState starts schedulers on boot | P0 | docker logs |
| TC-INT-04 | pg_cron virtual tags computed every 1min | P1 | psql |
| TC-INT-05 | influx_agg_1m continuous aggregate refresh | P1 | psql |
| TC-INT-06 | predictions row count grows every 10min cycle | P1 | psql |
| TC-INT-07 | NOTIFY/LISTEN alarm delivery within 15s | P1 | Playwright timed |
| TC-INT-08 | PerformanceAggregator writes hourly metrics | P2 | psql |
| TC-INT-09 | VirtualTagScheduler registers tags in `influx_tag` | P2 | psql |
| TC-INT-10 | data-injector container active; `influx_hist` grows over 30s | P0 | docker ps + psql |

## Section 4 — Smoke Test Suite (Tier-1, Every Commit)

Target: **exactly 10 cases, < 60 seconds total.**

| TC-ID | Test | Tool | Expected | Time |
|-------|------|------|----------|------|
| SMOKE-01 | `curl /_ping` | curl | HTTP 200 + "pong" | 1s |
| SMOKE-02 | DB connection (`psql -c "SELECT 1"`) | psql | "1 row" | 2s |
| SMOKE-03 | `/` dashboard | Playwright | title = "Dashboard \| KSYS" | 5s |
| SMOKE-04 | `/alarms` | Playwright | title = "Alarms" | 4s |
| SMOKE-05 | `/forecast` | Playwright | title contains "예측 플레이어" | 5s |
| SMOKE-06 | `/trend` | Playwright | title = "Trend Analysis" | 4s |
| SMOKE-07 | `/training-wizard` | Playwright | title NOT 404; step-1 visible | 5s |
| SMOKE-08 | `/ai` (intentional 404 sentinel) | Playwright | title = "404 - Not Found" (until registered) | 3s |
| SMOKE-09 | reflex-app container Up | docker ps | "Up" status | 2s |
| SMOKE-10 | `influx_hist` data freshness | psql | count > 0 over last 5min | 2s |
| | **Total** | | | **~33s** |

**SMOKE-08 sentinel**: if `/ai` ever passes (not 404), someone registered the page → the Day 6 SQL injection fix must be re-verified before merge.

**Run order**: SMOKE-01/02/09 first (infrastructure). If any fail, abort remaining.

## Section 5 — Regression Test Suite (Tier-3, Before RPI Deploy)

Target: 50 cases covering all M1 features + critical data flows. (Full table in original QA strategist output — abbreviated here by domain.)

| Domain | Regression case count | Critical handlers |
|--------|---------------------|-------------------|
| Alarm | 10 (REG-01..10) | acknowledge_alarm, acknowledge_selected, fetch_history, export_excel, cleanup_old_alarms |
| Forecast | 8 (REG-11..18) | load_deployed_models, select_model, ForecastScheduler 10-min, deploy_model, undeploy_model, delete_model, ActualValueUpdater |
| Training | 6 (REG-19..24) | initialize_wizard, next_step, create_feature_config, start_training, save_model, validation_feasibility |
| Sensor | 7 (REG-25..31) | load_tags, toggle_dashboard, toggle_alarm, add_tag, delete_tag, save_sensor_info, show_all_dashboard |
| Dashboard | 6 (REG-32..37) | start_streaming, _fetch_data, ScadaAlarmState toggle_streaming, set_severity_filter, AlarmMonitor 10s, NOTIFY delivery |
| Trend | 5 (REG-38..42) | TrendState.load, load_series_data, export_csv_all, export_csv_page, set_aggregation_view |
| Data Integration + Security + Infra | 8 (REG-43..50) | ForecastScheduler E2E, pg_cron virtual tags, continuous agg refresh, SchedulerState boot, communication heatmap, SQL injection trend, CORS, smoke pass |

## Section 6 — Cannot Automate Easily (Manual Verification)

| Item | Why Manual | Cadence |
|------|-----------|---------|
| Visual layout accuracy | Pixel diffs flaky across resolutions | Per release |
| Cloudflare tunnel public access | Requires live CF account + external network | Per deployment |
| Multi-RPI consistency | Need actual hardware | Monthly |
| User authentication coverage | None exists; will test when added | When added |
| pickle.loads security | Crafted malicious pickle dangerous to automate | Security review |
| AlarmScheduler (legacy psycopg2 thread) | Hard to introspect from async test | Logs monitoring monthly |
| DailyTrainingScheduler | Not wired into start_all() | After activation |
| SCADA NOTIFY reconnect on DB drop | Destructive test | Quarterly |
| Training wizard CPU-bound blocking | Requires load testing + asyncio profiler | Manual with profiler |
| KnowledgeFileWatcher hot reload | Filesystem events + timing | Manual when /ai active |

## Section 7 — Test Data Prerequisites

Seed script `scripts/seed_test_data.sql` (to be written) must populate:

| Dataset | Minimum | Why | Tables |
|---------|---------|-----|--------|
| `alarm_history` unacked | 5 rows with known event_ids | Acknowledge tests | alarm_history |
| `alarm_history` old acked (>7d) | 5 rows | cleanup_old_alarms | alarm_history |
| `influx_hist` sensor data | 48h × 2 tags, 1-min intervals | Chart/dashboard tests | influx_hist |
| `influx_qc_rule` thresholds | 2 tags with min/max | Badge logic, AlarmMonitor | influx_qc_rule |
| `viewer_tag` entries | 3 tags with mixed flags | Sensor tests | viewer_tag |
| `model_registry` deployed | 1 row `is_deployed=true, model_pickle NOT NULL` | Forecast tests | model_registry |
| `model_registry` saved (not deployed) | 2 rows | Deploy/undeploy tests | model_registry |
| `feature_config` | 1 complete config | Training tests | feature_config |
| `influx_tag` | All referenced tags | FK integrity | influx_tag |
| `predictions` | 10 rows (5 with actual, 5 without) | ActualValueUpdater test | predictions |

Script requirements:
1. `ON CONFLICT DO NOTHING` for idempotency
2. Target only `ecoanp` test DB — never production
3. Prefix test data: `tag_name='TEST_SENSOR_01'`, `event_id='TEST-ALM-001'`
4. Cleanup block: `DELETE FROM alarm_history WHERE event_id LIKE 'TEST-%'`
5. Relative timestamps: `NOW() - INTERVAL '24 hours'`

## Section 8 — Execution Priority (First 2 Weeks)

### Week 1: Ship Tier-1 Smoke Suite

| Day | Task | Owner | Output |
|-----|------|-------|--------|
| 1 | Write `scripts/seed_test_data.sql` | Backend dev | Idempotent seed |
| 2 | Implement SMOKE-01..10 as `scripts/smoke_test.sh` | QA/DevOps | <60s exit 0/1 |
| 3 | Verify smoke runs clean | QA | 10/10 green |
| 4 | Wire smoke to pre-push hook (or CI) | DevOps | `make smoke` |
| 5 | Document baseline failures | QA | Known-failure list |

### Week 2: Tier-2 Functional Coverage for M1

| Day | Task | Owner | Output |
|-----|------|-------|--------|
| 1-2 | Playwright Alarm domain (TC-ALARM-01..07) | QA | `tests/e2e/test_alarms.py` |
| 2-3 | Playwright Dashboard + Trend critical | QA | `tests/e2e/test_dashboard_trend.py` |
| 3-4 | pytest DB write handlers | Backend dev | `tests/unit/test_db_writes.py` |
| 4 | Scheduler smoke (docker logs + psql) | DevOps | Added to `smoke_test.sh` |
| 5 | Full Tier-2 end-to-end | QA | Baseline; document failures |

### Tier-3/4 Deferred

- Tier-3 (50 regression) before first RPI deployment
- Tier-4 (12 performance) monthly on actual RPI

## Appendix A — Known Issues Affecting Test Coverage

| Issue | Source | Test Implication |
|-------|--------|-----------------|
| `/ai` dead, Day 6 fix dead-path | playwright_test | SMOKE-08 sentinel; REG-48 must cover AI input when registered |
| `/alarms_rt` filter bar hardcoded literals | spec_01 Issue 2 | Document as P1 bug; cannot test filtering |
| Pagination buttons dead on realtime alarm pages | spec_01 Issue 3 | TC-ALARM-09 step 4 |
| `toggle_auto_refresh` dup-def (FIXED Day 2) | audit H-07 | Add introspection test to prevent regression |
| `overall_success_rate` >100% bug | spec_02 CommunicationState | Unit test with synthetic >100% data |
| `@rx.var` on pandas pivot not cached | audit MEDIUM | Render 20× rapid, check no degradation |
| HTTP 200 != page works (Reflex SPA) | playwright_test | SMOKE-03..07 use Playwright title check, not curl |
| 987 `print()` calls — UnicodeDecodeError risk | audit MEDIUM + user memory | Fixture captures print, asserts no error |

## Appendix B — Test Method Distribution

| Method | Test Count | % |
|--------|-----------|---|
| Playwright | 49 | 40% |
| pytest | 28 | 23% |
| psql direct | 20 | 16% |
| docker logs grep | 15 | 12% |
| curl/HTTP | 5 | 4% |
| Manual | 6 | 5% |
| **Total** | **123** | **100%** |

---

*End of spec_05_test_plan.md*
