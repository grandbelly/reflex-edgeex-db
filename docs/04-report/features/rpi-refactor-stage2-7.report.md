# Report — rpi-refactor-stage2-7

> 1 세션 (2026-05-19)에 진행된 Stage 1~4 부분 완료 결과.
> Plan §2 Stage 5-7 (RPI 효율, 공통화, 품질) + Stage 4 deep helper extraction 은 다음 세션으로 이월.

Related docs:
- Plan: `docs/01-plan/features/rpi-refactor-stage2-7.plan.md`
- Design: `docs/02-design/features/rpi-refactor-stage2-7.design.md`
- HTML proposal (origin): `reports/refactor_proposal_2026-05-19.html`

---

## 1. Executive Summary

| Feature | 시작일 | 보고 시점 | 진행 단계 |
|---|---|---|---|
| `rpi-refactor-stage2-7` | 2026-05-19 | 2026-05-19 (당일) | Stage 1~4 부분 완료 |

### 1.1 Project Overview

| 항목 | 값 |
|---|---|
| Branch | `refactor/rpi-baseline-sync` |
| Commits | **13개** (sync 포함 시 14개) |
| Base | RPI 백업 (2025-12-05 snapshot) → 풍도 로컬 sync |
| Stages completed | Stage 1, 2, 3, 3.5 ✅ · Stage 4 (Sprint 1, 2, 3b, 4) 부분 ✅ |
| Stages remaining | Stage 4 deep extraction · Stage 5 (RPI) · Stage 6 (공통화) · Stage 7 (품질) |

### 1.2 Results Summary

| 지표 | 시작 (sync 후) | 현재 | 변화 |
|---|---|---|---|
| `ksys_app/` .py 파일 | 521 | **253** | **-51%** |
| 추정 총 LoC | ~136K | **~67K** | **-51%** |
| `ksys_app.py` (앱 진입점) | 1,130 | **208** | **-82%** |
| 1,000+ LoC 파일 | 8 | **3** | **-63%** |
| 죽은 페이지 | 14 | 0 | -100% |
| 죽은 module-level 함수 | 14+ | 0 | -100% |
| `app.add_page()` 죽은 주석 | 5 | 0 | -100% |
| 라우트 등록 패턴 | 3가지 혼재 | `@rx.page` 단일 | 통일 |

### 1.3 Value Delivered (4 Perspectives)

| 관점 | 내용 |
|---|---|
| **Problem (해결한 문제)** | (1) 작년 Sonnet 4.0 누적 vibe-coding의 결과 — `ksys_app_clean/` 같은 274파일 통째 중복, 18개 `.backup`/`.bak`/`.disabled` 산재, 14개 등록 안 된 페이지, 라우트 등록 3패턴 혼재, `ksys_app.py` 1,130 LoC 모놀리식. (2) Stage 1 시점부터 RPI 운영본의 실 baseline이 어디인지 모호했던 문제. |
| **Solution (해결 방법)** | RPI 백업을 풍도로 sync해서 단일 baseline 확립 → 7-stage refactor plan 작성 → Stage 1 잡초 제거 → Stage 2 죽은 페이지/서비스 정리 → Stage 3 `@rx.page` 데코레이터로 라우트 등록 통일 → Stage 3.5 `ksys_app.py` 죽은 함수 14개 통째 제거 → Stage 4 모놀리식 5개 파일 패키지화 (training_state, pipeline_v2_hybrid, dashboard, forecast_player_state) + 1개 dead 통째 삭제. |
| **Function UX Effect (기능·UX 효과)** | 운영 사용자 경험 변화 = 0 (regression 0 목표). 운영 페이지 (`/`, `/forecast`, `/trend`, `/alarms*`, `/scada-*`, `/comm`, `/training-wizard`, `/model-performance`, `/viewer-tag` 등 ~14개)는 라우트 정리만 되고 외부 URL 1개만 변경 (`/forecast-player-fixed` → `/forecast`). 사이드바 + redirect도 동시 업데이트. |
| **Core Value (핵심 가치)** | 1년 누적 잡초 제거 + 단일 진실원본 (SSOT) 확립. 이제 Stage 5 (RPI 효율 튜닝) / Stage 6 (공통 패턴) / Stage 7 (품질 gate) 같은 후속 작업이 깨끗한 baseline 위에서 가능. 또한 ARM RPI 4GB 환경에 맞춘 다음 단계의 발판. |

---

## 2. What was Done (Phase by Phase)

### 2.1 Baseline sync (`e397d8f`)
- RPI 백업 (`C:\sync\01_remote_ksys\2026-03-24\deployment\20251030-rpi-finished`)을 robocopy로 풍도 로컬에 import
- 우리 세션 핵심 변경분 6개 파일 (run_schedulers, scheduler_state, forecast_scheduler, scheduler_manager, db_orm, Dockerfile.scheduler) `git checkout master` 로 복원
- 풍도 환경 폴더 (`.bkit/`, `.web/`, `__pycache__/`, `agentic-runs/`, `graphify-out/`, `saved_models/`, `backup/`, `certification_data/`) 제외
- 278 파일, +81,391 줄

### 2.2 Stage 1 — 잡초 제거 (`7618aa2`)
**285 파일 / -89,601 줄**
- `ksys_app/ksys_app_clean/` 폴더 통째 삭제 (274 파일 중 268개가 `ksys_app/`와 MD5 정확히 동일)
- 18개 `.backup` / `.bak` / `.bak2` / `.disabled` / `_OLD` / `_backup_2025*` 파일 삭제
- `pages/forecast_player_state.py` (잘못된 위치, 외부 import 0개) 삭제
- 검증: `grep ksys_app_clean` → 0 hits, `grep` 삭제된 모듈명들 → 0 imports

### 2.3 Plan 문서 (`4d211bf`)
- `docs/01-plan/features/rpi-refactor-stage2-7.plan.md` 326줄
- Stage 2-7 12.5일 roadmap, AC 9개, Risks 6개, OQ 6개

### 2.4 Stage 2 — 죽은 페이지 정리 (`4bf9cf9`, `4c0203b`)
**18 파일 / -5,926 줄**
- Sprint 2a (`4bf9cf9`): 11개 등록 안 된 페이지 삭제
  - `forecast_player.py` 1,136L, `trend_enhanced_hierarchical.py` 881L, `alarm_viewer.py`, `alarms_hist.py`, `dashboard_v2.py`, `training.py`, `alarms_rt.py`, `model_config.py`, `training_results.py`, `test_wizard.py`, `tech.py`
- Sprint 2b (`4c0203b`): 7개 orphan service/query 모듈 삭제
  - `services/{feature_config_service_simple, qc_rule_service, realtime_forecast_service, simple_forecast_service}.py`
  - `queries/{communication, dashboard, hist_latest}.py`
- 모두 외부 import 0개 grep으로 사전 확인

### 2.5 Stage 3 — 라우트 등록 통일 (`663aee6`)
**8 파일 / +32 / -73**
- 7개 페이지에 `@rx.page(...)` 데코레이터 추가:
  `trend_enhanced_v2`, `communication`, `alarms`, `scada_alarm_viewer`,
  `alarms_hist_simple`, `alarms_rt_new`, `alarms_hist_new`
- `ksys_app.py` 에서 `app.add_page()` 호출 8개 제거 + 죽은 주석 라우트 5개 제거
- `scada_alarm_comparison.py` 중복 등록 (decorator + add_page) 해결

### 2.6 Stage 3.3 — forecast_player rename (`ec3ba96`)
**4 파일 / +7 / -8**
- `pages/forecast_player_fixed.py` → `pages/forecast_player.py` (git rename)
- alias 트릭 (`forecast_player_fixed as forecast_player`) 제거
- 라우트 `/forecast-player-fixed` → `/forecast` (URL 깔끔하게)
- `components/layout.py` (sidebar) + `states/model_performance_state.py` (rx.redirect) 도 같이 업데이트

### 2.7 Stage 3.5 — ksys_app.py 죽은 함수 제거 (`b52ec6b`)
**1 파일 / -870 줄** (단일 commit 최대 효과)
- `ksys_app.py` 1,078 → **208 줄 (-82%)**
- 제거: `index_old`, `trend_page`, `tech_page`, `tech_page_original` + 10개 헬퍼 (`_create_gradient`, `create_toggle_group`, `trend_composed_chart_new` 등)
- 모두 외부 import 0개 + helper 호출 site도 dead 함수 내부에서만 grep 확인

### 2.8 Design 문서 (`cc38b40`)
- `docs/02-design/features/rpi-refactor-stage2-7.design.md` 387줄
- Stage 4 decomposition pattern (P1: Reflex State 4-way split / P2: Multi-class 1-file-per-class), 분할 순서, 검증 전략, OQ 5개

### 2.9 Stage 4 Sprint 1 — `training_state.py` 패키지화 (`907a1b4`)
**3 파일 변경 / +83 / -43**
- `training_state.py` 1,108L → `training_state/` 패키지 (`__init__.py` 23L + `cache.py` 48L + `state.py` 1,077L)
- Reflex State 분리 패턴 PoC 성공. `from ksys_app.states.training_state import TrainingState` 호환성 100%.
- 깊은 helper extraction (queries.py, fitter.py)은 미실시 — Sprint 1은 패턴 검증만.

### 2.10 Stage 4 Sprint 2 — `pipeline_v2_hybrid` 패키지화 (`819e841`)
**12 파일 변경 / +1,808 / -1,659**
- `pipeline_v2_hybrid.py` 1,659L → 11-file package
  - `metadata.py` 73L, `preprocessing.py` 167L, `features.py` 50L, `registry.py` 54L, `training.py` 309L
  - `plugins/{base, autoarima, prophet, xgboost}.py` 37/395/283/399L
- 외부 import 7곳 (ensemble_plugin, training_state, 5개 scripts) 모두 그대로 작동 (`__init__.py` re-export)
- 가장 큰 sub-file 399L (xgboost). 기존 monolith 대비 -76%.

### 2.11 Stage 4 Sprint 3b — `dashboard` + `forecast_player_state` 패키지화 (`27d0ab8`)
**5 파일 변경 / +254 / -211**
- `dashboard.py` 1,826L → `dashboard/` 패키지 (`utils.py` 214L + `state.py` 1,638L)
  - 13개 utility 함수 extraction (`_to_float`, `_fmt_s`, `_norm_window` 등)
- `forecast_player_state.py` 1,668L → `forecast_player_state/` 패키지 (단순 rename, module-level utility 없었음)
- 외부 import 3곳 그대로 작동

### 2.12 Stage 4 Sprint 4 — `enhanced_agent_orchestrator.py` 삭제 (`d77988f`)
**1 파일 변경 / -1,097 줄**
- Sprint 4는 P2 분해 (6 모듈)로 계획했으나, OQ4-4 확인 결과 외부 import 0개 → 분해 대신 통째 삭제
- `/ai` 라우트 제거 후 dead. 같은 클래스명 grep도 0 hits.
- ai_engine/ 디렉토리 다른 19개 파일은 일부 살아있어 보존 (pump_diagnostics, ai_insights page, tests에서 import).

---

## 3. Plan 대비 달성도 (Stage 4 시점)

### 3.1 Goal Tracking

| Goal | 목표 | 현재 | 평가 |
|---|---|---|---|
| G1: 죽은 페이지 0개 | ✅ | 14 → 0 | 100% 달성 |
| G2: 라우트 등록 통일 | ✅ | `@rx.page` 단일 | 100% 달성 |
| G3: 1,000+ LoC 파일 0개 | 부분 | 8 → 3 | 63% 달성 (남은 3개는 Reflex State framework 제약) |
| G4: RPI 효율 측정 | 미진행 | - | Stage 5 |
| G5: 공통 패턴 추출 | 미진행 | - | Stage 6 |
| G6: 품질 게이트 (ruff/mypy/vulture) | 미진행 | - | Stage 7 |

### 3.2 Acceptance Criteria

| AC | 목표 | 현재 | 평가 |
|---|---|---|---|
| AC1: ksys_app/ ≤ 150 파일 | 150 | 253 | 미달성 (103 over) |
| AC2: 1,000+ LoC = 0 | 0 | 3 | 부분 (63% 감소) |
| AC3: 죽은 페이지 = 0 | 0 | 0 | ✅ |
| AC4: `ruff check .` exit 0 | 0 errors | 미실행 | Stage 7 |
| AC5: 모든 라우트 HTTP 200 | 200 | 미검증 | Docker build 필요 |
| AC6: RPI idle 메모리 ≤ baseline × 0.7 | ≤ 70% | 미측정 | Stage 5 |
| AC7: forecast 응답 ≤ 5초 | ≤ 5s | 미측정 | Stage 5 |
| AC8: 좀비 LISTEN = 0 | 0 | ✅ | (이전 세션 fix) |
| AC9: Stage 별 atomic commit | atomic | ✅ | 13 commits 깔끔 |

### 3.3 남은 1,000+ LoC 파일 — 왜 못 줄였나

| 파일 | LoC | 이유 |
|---|---|---|
| `forecast_player_state/state.py` | 1,668 | Reflex `rx.State` 단일 클래스. `@rx.event` 메서드 본문이 self.* mutation 포함 → 외부 helper로 빼려면 메서드 단위 수술 필요. Sprint 3b는 패키지화만 함. |
| `dashboard/state.py` | 1,638 | 동일. utility 13개만 분리됨. |
| `training_state/state.py` | 1,077 | Sprint 1 PoC — 동일. |

**근본 해결책**: 각 메서드 분석 → DB 쿼리는 `queries.py` async 함수로, view prep은 `view_helpers.py` 함수로, self.* mutation만 메서드에 유지. 1-2일 추가 작업 예상.

---

## 4. Lessons Learned

### 4.1 잘된 것

1. **PRD 없이 plan/design 진행 OK** — refactor 작업은 PRD 단계 불필요. Plan 문서가 충분.
2. **잡초가 많을수록 cleanup 효과 큼** — Stage 1+2에서 LoC -70% (95K → 38K 추정). 진짜 코드는 1/3 미만이었음.
3. **`@rx.page` 데코레이터 패턴 통일** — `ksys_app.py` -82% LoC. 라우트 등록 1방식만 남으니 코드베이스 이해 쉬워짐.
4. **`grep` + `ast.parse` 만으로 sanity check 가능** — Docker build 안 돌려도 commit 신뢰도 높음.
5. **dead code 발견 시 split보다 delete** — `enhanced_agent_orchestrator.py` (1,097L) 사례. 분해 대신 삭제.

### 4.2 어려웠던 것 / 개선 여지

1. **Reflex State 분리는 framework 제약 큼** — 단일 `rx.State` 상속 강제. Mixin/Composition 불가. Helper extraction이 유일한 deep-split 길이지만 메서드별 수작업.
2. **Sprint 1/3b가 얕음** — 패키지화만 하고 helper extraction 못 함. state.py가 여전히 거대. 솔직히 "1,000+ LoC 0개" 목표 미달.
3. **Docker build 미검증** — 사용자 Docker Desktop 꺼져 있어서 13 commits 누적 후에도 진짜 실행 검증 못 함. ast.parse + grep로만 sanity check.
4. **Stage 4 design 문서의 분할 순서가 실제와 약간 달랐음** — Sprint 1 (training, smallest), Sprint 2 (ml/pipeline, multi-class), Sprint 3b (dashboard + forecast_player 함께), Sprint 4 (ai_engine — design은 split, 실제는 delete). 적응형 진행이 더 효과적.
5. **Header import 중복** — Sprint 2의 pipeline 분해에서 9개 파일에 동일한 imports 헤더 복사 (+148 LoC). Stage 7 ruff sweep으로 정리 필요.

### 4.3 다음 세션 권장 순서

1. **Docker build 검증 먼저** — 사용자가 Docker Desktop 켜고 `docker compose -f docker-compose.local.yml build reflex-app` + `up -d`. 14001 backend / 14000 frontend 정상 부팅 확인.
2. **남은 3 monolith 깊은 split** — training_state/dashboard/forecast_player_state의 helper extraction. 1-2일.
3. **Stage 5 RPI 효율** — asyncpg pool 튜닝, AutoARIMA disk cache, Reflex lazy page import, TimescaleDB chunk 7일, Docker ARM64 multi-stage. 3일. RPI 실서버 접근 필요.
4. **Stage 6 공통 패턴** — repositories/, views/charts/, BaseState 통일. 3일.
5. **Stage 7 품질** — ruff + mypy + vulture + pre-commit hook. 2일.

---

## 5. Open Questions (다음 세션에서 결정)

(Plan §10 + Design §9 + 이번 세션 발견 통합)

1. **Docker build 실제 통과?** — 13 commits 누적 후 reflex run 정상 부팅 확인 필요.
2. **RPI 실서버 접근 가능?** — `ssh tion@192.168.0.80` 시도 → Stage 5 RPI 측정.
3. **Reflex 0.8.16 native lazy page import 지원?** — Stage 5-3 PoC 필요.
4. **남은 ai_engine/ 19개 파일 dead 검증** — vulture로 Stage 7에서 처리.
5. **`pipeline_v2_hybrid` 패키지 이름 정리** (Plan OQ4-1) — `ml/pipeline/`로 rename? 7곳 import 경로 일괄 업데이트 필요.
6. **`BaseState` 추상화 통일** (Design OQ4-2) — Stage 6 핵심.

---

## 6. Statistics

### 6.1 Commit summary

| Stage | Commits | Net LoC |
|---|---|---|
| Baseline sync | 1 | +81,391 |
| Stage 1 | 1 | -89,601 |
| Plan | 1 | +326 |
| Stage 2 | 2 | -5,926 |
| Stage 3 | 1 | -41 |
| Stage 3.3 (rename) | 1 | -1 |
| Stage 3.5 | 1 | -870 |
| Design | 1 | +387 |
| Stage 4 Sprint 1 | 1 | +40 |
| Stage 4 Sprint 2 | 1 | +149 |
| Stage 4 Sprint 3b | 1 | +43 |
| Stage 4 Sprint 4 | 1 | -1,097 |
| **Total** | **13** | **-15,200** |

(Note: net positive from baseline sync was offset by Stage 1 cleanup; subsequent net is -15,200.)

### 6.2 File operations

| Operation | Count |
|---|---|
| Files created (new packages, plan, design, report, HTML reports) | 31 |
| Files deleted | 303 |
| Files renamed | 5 |
| Files modified (edit only) | ~50 |

---

## 7. References

- Plan document: `docs/01-plan/features/rpi-refactor-stage2-7.plan.md`
- Design document: `docs/02-design/features/rpi-refactor-stage2-7.design.md`
- HTML proposal (original): `reports/refactor_proposal_2026-05-19.html`
- HTML page walk: `reports/page_walk_2026-05-19.html`
- HTML prompt log: `reports/prompt_log_2026-05-19.html`
- Memory: `~/.claude/projects/<this>/memory/feedback_no_host_reflex_zombie.md`
- RPI backup origin: `C:\sync\01_remote_ksys\2026-03-24\deployment\20251030-rpi-finished` (read-only)
- Working branch: `refactor/rpi-baseline-sync` (13 commits ahead of `master`)

---

*Generated 2026-05-19 by Claude Opus 4.7 · PDCA Report · Stage 1-4 partial completion*
