# Plan — rpi-refactor-stage2-7

> RPI 환경 최적 운영을 위한 ksys_app 리팩토링 Stage 2-7 (Stage 1은 완료).
> 단일 Reflex 모놀리식 앱을 작년 Sonnet 4.0 코드 품질에서 ARM/저메모리 최적 운영본으로 전환.

---

## Executive Summary

| Feature | 시작일 | 예상 완료일 | 기간 |
|---|---|---|---|
| `rpi-refactor-stage2-7` | 2026-05-19 | 2026-06-04 | 약 12.5 영업일 |

### 1.1 Project Overview

- **Baseline:** RPI 백업 (2025-12-05 마지막 변경) 풍도 로컬로 동기화 완료, 새 브랜치 `refactor/rpi-baseline-sync`
- **Stage 1 완료:** ksys_app_clean/(274 파일) + 18개 데드 파일 + 1개 잘못된 위치 파일 삭제 → ksys_app/ 521 → 262 파일 (-50%)
- **Target Hardware:** Raspberry Pi 4/5 (ARM64, 4GB RAM, SD card I/O)
- **Stack:** Reflex 0.8.16 + TimescaleDB 2 + statsforecast (AutoARIMA) + Docker Compose

### 1.2 Results Summary (예상)

| 지표 | Stage 1 시점 | Stage 7 완료 시 | 변화 |
|---|---|---|---|
| 총 LoC | ~47,000 | ~35,000 | -25% |
| .py 파일 | 262 | ~150 | -43% |
| 1,000+ LoC 거대 파일 | 8 | 0 | -100% |
| Docker 이미지 (ARM64) | 측정 필요 | -30% | ↓ |
| RPI 부팅 시간 | 측정 필요 | -50% | ↓ |
| RPI idle 메모리 | 측정 필요 | -30% | ↓ |
| 좀비 LISTEN 발생률 | 0 (이미 fix) | 0 | ✅ |

### 1.3 Value Delivered (4 Perspectives)

| 관점 | 내용 |
|---|---|
| **Problem (해결할 문제)** | 작년 Sonnet 4.0이 생성한 ksys_app은 N-버전 페이지 공존, 1,000+ LoC 모놀리식 state, eager import, asyncpg pool 무튜닝으로 RPI에서 OOM·부팅 지연·SD I/O 과다 발생. |
| **Solution (해결 방법)** | Stage 2(죽은 페이지) → Stage 3(라우트 통일) → Stage 4(모놀리식 분해) → Stage 5(RPI 효율) → Stage 6(공통 패턴) → Stage 7(품질). 매 단계 git commit + docker build 검증 게이트. |
| **Function UX Effect (기능·UX 효과)** | 17개 운영 페이지만 깔끔히 노출, 페이지별 lazy load로 RPI 부팅 빠르게, AutoARIMA 모델 캐시로 forecast 응답 안정. 24/7 운영 안정성 ↑. |
| **Core Value (핵심 가치)** | 1년 누적된 vibe-coding 잡초 정리 + RPI 운영본 정착. 다음 신규 기능을 안정 baseline 위에 쌓을 수 있는 "정리된 단일 진실원본(SSOT)". |

---

## 2. Background & Context

### 2.1 어떻게 여기까지 왔는가
- 2025 ~ 작년 Sonnet 4.0으로 ksys_app 다수 페이지/state 작성 → v1/v2/_new/_enhanced 패턴이 중첩되며 누적
- 2025-11 ~ 12 RPI 환경에서 추가 작업 → `ksys_app_clean/` 이라는 부분 리팩토링 시도가 진행됐으나 본체와 거의 중복 (268/274 MD5 동일)으로 방치
- 2026-05-19 풍도 로컬에서 fullstack 검증 중 RPI 백업 폴더와의 divergence 발견, baseline 동기화 후 본 리팩토링 착수

### 2.2 RPI 운영 제약 (설계 전제)
1. **메모리**: 4GB 총량 중 OS·Docker overhead 제외하면 앱이 쓸 수 있는 게 약 2~2.5GB
2. **CPU**: ARM64 4코어, statsforecast 같은 NumPy heavy 작업은 1코어 기준으로 설계
3. **디스크**: SD card I/O 느림 — 청크 빈번 쓰기 회피, hypertable 청크 간격 늘리기
4. **네트워크**: 로컬 LAN만, cloudflared 사용 시 추가 latency
5. **재부팅**: 정전 잦음 → graceful shutdown + auto-restart 견고해야 함 (Stage 1 schedulers 좀비 fix가 이미 처리)

---

## 3. Goals & Non-Goals

### 3.1 Goals
- [G1] **죽은 페이지 0개**: 라우트 등록 안 된 14개 pages/*.py 정리
- [G2] **라우트 등록 패턴 단일화**: `@rx.page` 데코레이터 + 모듈 자동 디스커버리로 통일
- [G3] **1,000+ LoC 파일 0개**: 모놀리식 state/page 8개를 단일 책임 모듈로 분해
- [G4] **RPI 효율 측정 가능**: asyncpg pool, AutoARIMA 캐시, lazy import 적용 후 부팅·메모리 측정
- [G5] **공통 패턴 추출**: repositories/ + views/charts/ + BaseState 도입
- [G6] **품질 게이트**: ruff + mypy + vulture + pre-commit hook 정착

### 3.2 Non-Goals (이번 작업 범위 밖)
- 신규 기능 추가 (alarm 새 규칙, dashboard 신규 위젯 등) — refactor only
- TimescaleDB hypertable 스키마 변경 — Stage 5 청크 튜닝만, 컬럼 추가/삭제 X
- Reflex 0.8 → 0.9 마이그레이션
- 프론트엔드 Tailwind 디자인 시스템 전면 개편 (별도 작업)
- statsforecast 대체 검토 (Prophet, uvarima 등) — 별도 RFC

---

## 4. Scope (Stage 별 상세)

### Stage 1 ✅ COMPLETED (commit 7618aa2)
- ksys_app_clean/ 274 파일 삭제
- .backup/.bak/.bak2/.disabled/_OLD 18개 데드 파일 삭제
- pages/forecast_player_state.py (잘못된 위치) 삭제

### Stage 2 — 죽은 페이지 정리 (1일)
**In-Scope:**
- ksys_app.py가 import/add_page 안 하는 페이지 14개 정리
  - 삭제 후보 (확인된 죽음): forecast_player.py, forecast_player_state.py(이미 삭제), dashboard_v2.py, alarms_hist.py, alarms_rt.py, alarm_viewer.py, training.py, training_results.py, test_wizard.py, tech.py, trend_enhanced_hierarchical.py
  - 확인 필요: model_config.py (dashboard에서 처리하는지)
- 각 페이지의 backend dependency (services/, queries/) 검색 → 다른 페이지에서도 안 쓰면 함께 제거

**Acceptance:**
- `grep -r "from .pages.{deleted_name}" --include="*.py"` → 0 hits
- docker build 통과
- 라우트 21 → 17개로 정돈

### Stage 3 — 라우트 등록 통일 (0.5일)
**In-Scope:**
- `ksys_app.py`의 3가지 등록 방식 통일 → `@rx.page` 데코레이터 패턴
- alias 트릭 (`from .pages import forecast_player_fixed as forecast_player`) 제거 → 페이지 파일을 `forecast_player.py`로 rename
- 주석된 죽은 add_page 라인 모두 제거
- `ksys_app/routes.py` (또는 `pages/__init__.py`) 신규: 자동 디스커버리 로직

**Before/After Example:**
```python
# Before (ksys_app.py에 명시)
from .pages.alarms import alarms_page
app.add_page(alarms_page, route="/alarms", on_load=[AlarmsState.initialize, ...])

# After (pages/alarms.py에 데코레이터)
@rx.page(route="/alarms", title="Alarms",
         on_load=[AlarmsState.initialize, DashboardRealtimeState.start_streaming])
def alarms_page():
    ...
# ksys_app.py 는 그냥
from . import pages  # 모듈 import만으로 @rx.page 트리거
```

**Acceptance:**
- ksys_app.py 라인 수 1,057 → ~400 (라우트 등록 로직 분리)
- 죽은 주석 라우트 0개
- 모든 페이지 정상 부팅

### Stage 4 — 모놀리식 분해 (3일)
**Target 6 files (1,000+ LoC):**
1. `states/dashboard.py` 1,717 → `dashboard/{state, handlers, queries, view_helpers}.py` (각 ≤ 500)
2. `states/forecast_player_state.py` 1,668 → 동일 패턴 4분할
3. `ai_engine/enhanced_agent_orchestrator.py` 1,032 → `agents/` 디렉토리로 핸들러별 분리
4. `ksys_app.py` 1,057 → `{app, routes, lifecycle}.py` (App 인스턴스 + 라우트 + startup/shutdown 분리)
5. `ml/pipeline_v2_hybrid.py` 1,352 → `pipeline/{features, models, fitter, predictor}.py`
6. `states/training_state.py` 946 → 동일 4분할

**원칙:**
- 1 파일 ≤ 300 LoC (강제), ≤ 500 LoC (권장)
- Reflex State 클래스는 1개 유지하되 내부 메서드를 모듈로 import (functools.partial 또는 mixin)
- 분할 후 import만 바뀌고 기능은 동일 — diff 매 step별 < 200 줄로 reviewable

**Acceptance:**
- 모든 1,000+ LoC 파일 0개
- 기존 페이지 모두 정상 부팅
- gap-detector 또는 docker logs로 import error 0

### Stage 5 — RPI 효율 최적화 (3일)
**5-1. asyncpg pool 튜닝** (`db_orm.py` 또는 `db.py`)
```python
pool = await asyncpg.create_pool(
    dsn=DSN,
    min_size=1, max_size=4,
    max_inactive_connection_lifetime=120,
    command_timeout=30,
)
```

**5-2. AutoARIMA 모델 디스크 캐시 + re-fit 주기 분리**
- `model_registry.pickle_data`를 매 cycle re-fit 대신 1일/1주 주기로
- forecast_scheduler.py에서 caching 로직 추가
- season_length RPI 부담 줄이기 (144 → 24 또는 36)

**5-3. Reflex 페이지 lazy import**
- ksys_app.py 부팅 시 16개 페이지 eager import → 라우트 호출 시점 lazy
- Reflex 0.8 native 지원 여부 확인 필요 (안 되면 dict-based lazy loader)

**5-4. TimescaleDB 청크 튜닝** (`migrations/`에 새 .sql 추가)
```sql
SELECT set_chunk_time_interval('influx_hist', INTERVAL '7 days');
ALTER TABLE influx_hist SET (timescaledb.compress);
SELECT add_compression_policy('influx_hist', INTERVAL '7 days');
```

**5-5. Docker 이미지 ARM 최적화**
- `Dockerfile` base: `python:3.11-slim-bookworm` (ARM64 native)
- multi-stage build: builder + runtime
- `.dockerignore` 강화

**5-6. uvicorn worker 1 고정**
- 이미 Stage 1 commit으로 적용됨 (run_schedulers.py graceful shutdown + init: true)

**Acceptance:**
- RPI 실서버 부팅 후 측정: 부팅 시간 / idle 메모리 / forecast 응답 시간
- 베이스라인 대비 ≥ 30% 개선 1개 이상

### Stage 6 — 공통 패턴 추출 (3일)
**In-Scope:**
- `repositories/` 신규: SensorRepo, ModelRepo, ForecastRepo
  - 현재 dashboard/trend/alarm/forecast 4곳에 중복된 asyncpg 쿼리 통합
- `views/charts/` 공통 Plotly 헬퍼: `timeseries_chart`, `gauge_chart`
- `BaseState` 확장: loading/error/refresh_interval 공통 lifecycle
- 알람 severity 매핑 / 센서 unit 매핑 / tag hierarchy → `config/` 모듈

**Out-of-Scope:**
- 신규 component 추가 (디자인 변경)
- 페이지 레이아웃 개편

**Acceptance:**
- 중복 SQL 쿼리 ≥ 50% 감소 (vulture / 단순 grep)
- repositories/ 모듈 단위 테스트 (tests/repositories/) 존재

### Stage 7 — 코드 품질 보강 (2일)
**In-Scope:**
- `pyproject.toml`에 ruff 룰 정의 (line-length 100, F401/E501/B 등)
- mypy strict 모드 점진 적용 (먼저 ksys_app/states/만)
- over-broad `except Exception` 색출 → 구체 예외
- vulture로 dead import/function 자동 검출
- async 정합성 (blocking call 색출)
- `pre-commit` hook 셋업

**Acceptance:**
- `ruff check .` → 0 errors
- `vulture .` 결과 false-positive 제외 0 dead
- pre-commit hook 동작 확인

---

## 5. Approach

### 5.1 작업 단위 (Atomic Commits)
- 1 commit = 1 Stage 의 1 subtask (Stage 4-1, 4-2, 4-3 등)
- 매 commit 후 docker build 또는 import sanity check
- 깨지면 즉시 revert + 원인 분석

### 5.2 Branch 전략
- `refactor/rpi-baseline-sync` (현재) → Stage 7까지 진행
- 완료 후 master로 merge (squash X, history 보존)
- 단계별로 `--no-ff` merge 표시 가능

### 5.3 검증 게이트
| Stage | 검증 방식 |
|---|---|
| 2 | `grep` 깨진 import 0개 + docker build pass |
| 3 | docker compose up + 모든 라우트 HTTP 200 |
| 4 | 분할 전후 페이지 동작 동일 (스크린샷 또는 page_walk_*.html) |
| 5 | RPI 실서버 부팅·메모리·forecast latency 측정 |
| 6 | 단위 테스트 + 회귀 테스트 |
| 7 | `ruff` + `mypy` + `vulture` 통과 |

### 5.4 ⚠️ Stage 5 RPI 검증 종속성
- Stage 5 일부 항목(부팅·메모리 측정)은 **실제 RPI 디바이스에서만 가능**
- 사전 확인: `ssh tion@192.168.0.80` 접근 가능 여부, RPI 디스크 여유

---

## 6. Acceptance Criteria (전체)

- [AC1] ksys_app/ .py 파일 수 ≤ 150
- [AC2] 1,000+ LoC 파일 = 0
- [AC3] 죽은 페이지 (등록 안 된 라우트) = 0
- [AC4] `ruff check .` exit 0
- [AC5] docker compose -f docker-compose.local.yml up → 모든 라우트 HTTP 200
- [AC6] RPI 실서버 idle 메모리 ≤ baseline × 0.7
- [AC7] forecast 1-cycle (10분 간격) 응답 시간 ≤ 5초
- [AC8] graceful shutdown 좀비 LISTEN 발생률 0 (이미 통과)
- [AC9] git log에 Stage 별 명확한 commit chain

---

## 7. Risks & Mitigations

| 리스크 | 확률 | 영향 | 완화 |
|---|---|---|---|
| Stage 4 분할 중 hidden import 누락으로 페이지 깨짐 | 중 | 중 | 매 분할 후 즉시 docker build + grep import check |
| Reflex 0.8이 lazy page import 미지원 | 중 | 중 | Stage 5-3 PoC 먼저, 안 되면 dict-based loader로 우회 |
| RPI 실서버 접근 불가 | 낮 | 높 | Stage 5 RPI-specific 항목은 로컬 Docker(arm64 emulation)로 대체 측정 |
| forecast_player_state.py RPI 버전(1,668 LoC)과 우리 변경분 차이로 인한 regression | 중 | 중 | gap-detector 또는 Stage 4 분할 전 diff 검토 commit |
| statsforecast/AutoARIMA 모델 캐시 잘못 적용해서 stale prediction | 낮 | 높 | re-fit 주기 + version stamp + rollback 메커니즘 (Stage 5-2) |
| 작업 중 사용자 우선순위 변경 (긴급 버그 등) | 중 | 낮 | Stage 단위가 작아 어느 Stage 끝나도 안정 baseline |

---

## 8. Timeline

| 날짜 | Stage | 산출물 |
|---|---|---|
| 2026-05-19 (오늘) | Stage 1 ✅ | commit 7618aa2: -89,601 줄, 285 파일 삭제 |
| 05-20 | Stage 2 | 죽은 페이지 14개 정리 commit |
| 05-21 (오전) | Stage 3 | 라우트 등록 통일 commit |
| 05-21 (오후) ~ 05-23 | Stage 4 | 모놀리식 6개 분해 (6 commits) |
| 05-24 ~ 05-28 | Stage 5 | RPI 효율 6항목 (6 commits) |
| 05-29 ~ 06-02 | Stage 6 | 공통 패턴 추출 (3-4 commits) |
| 06-03 ~ 06-04 | Stage 7 | ruff + mypy + vulture + pre-commit |
| 06-05 | Final | gap-detector + report-generator + master merge |

총 약 **12.5 영업일** (1 dev). 병렬 작업 시 단축 가능 (Stage 4-7 일부 독립).

---

## 9. Dependencies

### 9.1 External
- Docker Desktop 가동 중 (현재 꺼짐, 사용자가 켜야 검증 가능)
- RPI 실서버 SSH 접근 (`192.168.0.80`) — Stage 5 검증에 필요
- TimescaleDB extension 활성 (이미 dev DB 있음)

### 9.2 Internal Codebase
- Stage 2 → Stage 1 commit 7618aa2 base
- Stage 3 → Stage 2 의 죽은 페이지 정리 완료
- Stage 4 → Stage 2-3 의 라우트 정돈 완료
- Stage 5-3 (lazy import) → Stage 4 의 ksys_app.py 분리 완료
- Stage 6 → Stage 4 의 모듈 분해 완료 (잡초 위에 추상화 X)
- Stage 7 → Stage 6 완료 (안정된 구조 위에 quality gate)

---

## 10. Open Questions

1. **OQ1**: Reflex 0.8.16이 page-level lazy import를 native 지원하는가? → Stage 5-3 시작 전 PoC 필요
2. **OQ2**: RPI 실서버 접근 가능 여부 확인 후 Stage 5 일정 확정
3. **OQ3**: `model_config.py` 페이지가 정말 죽었는지 dashboard와의 관계 확인 필요 (Stage 2)
4. **OQ4**: `ksys_app/scripts/seed_fake_model.py`, `trigger_forecast_once.py` 운영 baseline에 포함할지 (개발 도구로 남길지)
5. **OQ5**: AutoARIMA → 다른 모델 (Prophet, uvarima) 전환 별도 RFC 필요 — 본 plan 범위 밖
6. **OQ6**: forecast_player_state.py RPI 버전(1,668)과 우리 변경분 차이는 Stage 4 시작 전 review 필요

---

## 11. References

- `reports/refactor_proposal_2026-05-19.html` — 본 plan의 source HTML 제안서
- `reports/page_walk_2026-05-19.html` — 21-route fullstack 검증 결과
- `reports/prompt_log_2026-05-19.html` — 본 세션 prompt log
- commit `7618aa2` — Stage 1 baseline cleanup
- commit `e397d8f` — RPI baseline sync
- `~/.claude/projects/<this>/memory/feedback_no_host_reflex_zombie.md` — 좀비 LISTEN 진단·해결 메모

---

*Generated 2026-05-19 by Claude Opus 4.7 · PDCA Plan template · 12.5-day refactor roadmap*
