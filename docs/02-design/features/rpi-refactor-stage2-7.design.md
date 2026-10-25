# Design — rpi-refactor-stage2-7 (Stage 4 monolith split)

> Plan §4 Stage 4의 구체적 분해 설계. 5개 1,000+ LoC 파일을 어떤 모듈 구조로,
> 어떤 패턴으로, 어떤 순서로 나눌지의 청사진.

Plan reference: `docs/01-plan/features/rpi-refactor-stage2-7.plan.md`

---

## Executive Summary

| Stage 4 작업 | Before | After | 일정 |
|---|---|---|---|
| `states/dashboard.py` 분해 | 1,826 LoC × 1 | 4 모듈 × ~450 LoC | 0.6일 |
| `states/forecast_player_state.py` | 1,668 × 1 | 4 모듈 × ~420 LoC | 0.6일 |
| `states/training_state.py` | 1,108 × 1 | 4 모듈 × ~280 LoC | 0.4일 |
| `ml/pipeline_v2_hybrid.py` | 1,659 × 1 | 9 모듈 × ~180 LoC | 0.8일 |
| `ai_engine/enhanced_agent_orchestrator.py` | 1,097 × 1 | 6 모듈 × ~180 LoC | 0.6일 |
| **합계** | **5 파일 / 7,358 LoC** | **27 모듈** | **3 영업일** |

### Value Delivered (4 Perspectives)

| 관점 | 내용 |
|---|---|
| **Problem** | Reflex State 한 클래스가 1,000~1,800 LoC. 메서드 검색·코드 리뷰 어려움. Stage 5 RPI 효율 작업의 lazy import 적용 불가 (한 파일에 모든 게 묶임). |
| **Solution** | 책임별 4분할 패턴 (state vars / handlers / queries / view helpers) + ML 파이프라인 plugin별 분할 + Agent별 파일 분리. Reflex State는 단일 클래스 유지하되 비즈니스 로직을 외부 helper 함수로 분리. |
| **Function UX Effect** | 사용자 가시 기능은 동일 (regression 0 목표). 개발자 입장에선 한 페이지 변경 시 ~400L 파일 하나만 보면 됨. |
| **Core Value** | 다음 단계(Stage 5 RPI 효율, Stage 6 공통 패턴, Stage 7 quality)의 baseline. 모놀리식 상태에선 어떤 후속 작업도 위험. |

---

## 1. Current State Analysis

### 1.1 5개 monolith 파일 구조

#### A. `states/dashboard.py` (1,826 LoC)
```
22-225  : 13개 utility 함수 (_to_float, _fmt_s, _norm_window, _mean_safe, _compute_indicators_fallback, ...)
227-1826: class DashboardState(rx.State) — 단일 거대 클래스
```

#### B. `states/forecast_player_state.py` (1,668 LoC)
```
16-1668: class ForecastPlayerState(BaseState) — 단일 거대 클래스 (alias: FPS)
```

#### C. `states/training_state.py` (1,108 LoC)
```
20-50   : 3개 cache utility (_cache_training_result, _get_cached_model, _clear_cache)
53-1108 : class TrainingState(rx.State) — 단일 거대 클래스
```

#### D. `ml/pipeline_v2_hybrid.py` (1,659 LoC) — 다중 클래스
```
55     : PipelineMetadata (dataclass)
111-231: PreprocessingStep (ABC) + InterpolateStep + RemoveOutliersStep + ScaleStep
232-260: PreprocessingChain
261-293: FeatureEngineeringChain
294-313: ModelPlugin (ABC)
314-690: AutoARIMAPlugin (377 LoC) ← largest
691-955: ProphetPlugin (265 LoC)
956-1336: XGBoostPlugin (381 LoC)
1337-1373: ModelRegistry
1374-1659: TrainingPipelineV2
```

#### E. `ai_engine/enhanced_agent_orchestrator.py` (1,097 LoC)
```
18-33  : load_env() + AgentContext dataclass
34-64  : BaseAgent
65-506 : EnhancedResearchAgent (442 LoC) ← largest
507-639: EnhancedAnalysisAgent (133 LoC)
640-765: EnhancedReviewAgent (126 LoC)
766-1097: EnhancedMultiAgentOrchestrator (331 LoC)
```

---

## 2. Decomposition Pattern

### 2.1 Pattern P1 — Reflex State 4-way split (A/B/C용)

Reflex State는 **단일 클래스 유지** (rx.State 상속, framework 제약).
대신 **비즈니스 로직을 외부 helper 함수로 분리**해서 State 메서드는 얇은 wrapper로 유지.

```
states/dashboard/
├── __init__.py           # re-export: from .state import DashboardState
├── utils.py              # 순수 함수 (_to_float, _fmt_s, _norm_window 등) — 다른 State에서도 import 가능
├── queries.py            # async DB 쿼리 함수 (asyncpg 직접)
├── view_helpers.py       # chart/table prep 함수 (DB → frontend dict 변환)
└── state.py              # DashboardState 클래스 — vars + @rx.event handlers (얇음)
```

**state.py 예시:**
```python
import reflex as rx
from .queries import fetch_sensor_window, fetch_kpis
from .view_helpers import to_chart_payload
from .utils import _fmt_s

class DashboardState(rx.State):
    # State vars (그대로)
    sensors: list[dict] = []
    selected_window: str = "1h"

    @rx.event(background=True)
    async def load(self):
        async with rx.lock():
            pool = get_pool()
            rows = await fetch_sensor_window(pool, self.selected_window)  # ← 외부 helper
            self.sensors = to_chart_payload(rows)                          # ← 외부 helper

    @rx.event
    def set_window(self, window: str):
        self.selected_window = _norm_window(window)                        # ← utils
```

이 패턴의 장점:
- 단위 테스트 가능 (helper 함수는 pure, State 없이 import 가능)
- 다른 State에서도 utility/queries 재사용 가능 (Stage 6 공통화)
- 한 파일이 ~300-500 LoC로 유지
- @rx.event 데코레이터 동작 보존 (Reflex의 reactive 시스템 그대로)

### 2.2 Pattern P2 — Multi-class file → 1 class per file (D/E용)

각 클래스를 자체 파일로:

```
ml/pipeline/
├── __init__.py           # re-export: from .training import TrainingPipelineV2 등
├── metadata.py           # PipelineMetadata
├── preprocessing.py      # PreprocessingStep + 3 subclasses + PreprocessingChain
├── features.py           # FeatureEngineeringChain
├── plugins/
│   ├── __init__.py       # re-export plugins
│   ├── base.py           # ModelPlugin ABC
│   ├── autoarima.py      # AutoARIMAPlugin
│   ├── prophet.py        # ProphetPlugin
│   └── xgboost.py        # XGBoostPlugin
├── registry.py           # ModelRegistry
└── training.py           # TrainingPipelineV2
```

```
ai_engine/agents/
├── __init__.py           # re-export
├── context.py            # AgentContext + load_env
├── base.py               # BaseAgent
├── research.py           # EnhancedResearchAgent
├── analysis.py           # EnhancedAnalysisAgent
├── review.py             # EnhancedReviewAgent
└── orchestrator.py       # EnhancedMultiAgentOrchestrator
```

### 2.3 Backward compatibility (외부 import 보존)

```python
# 기존 외부 코드:
from edgeex_app.states.dashboard import DashboardState  # ← 깨지면 안 됨

# 새 구조:
edgeex_app/states/dashboard/__init__.py:
    from .state import DashboardState
    __all__ = ["DashboardState"]

# 같은 import 경로 그대로 동작 ✅
```

`states/dashboard.py` (단일 파일) → `states/dashboard/__init__.py` + `state.py` (패키지). Python은 둘 다 `from edgeex_app.states.dashboard import DashboardState` 로 import 가능. **호환성 100%**.

---

## 3. Target Architecture

### 3.1 디렉토리 트리 (Stage 4 완료 후)

```
edgeex_app/
├── states/
│   ├── dashboard/              # was 1,826 LoC single file
│   │   ├── __init__.py
│   │   ├── utils.py            (~200 LoC)
│   │   ├── queries.py          (~400 LoC)
│   │   ├── view_helpers.py     (~500 LoC)
│   │   └── state.py            (~700 LoC)
│   ├── forecast_player/        # was 1,668 LoC
│   │   ├── __init__.py
│   │   ├── queries.py          (~400 LoC)
│   │   ├── view_helpers.py     (~500 LoC)
│   │   ├── countdown.py        (~200 LoC) ← timer/scheduler helper
│   │   └── state.py            (~600 LoC)
│   ├── training/               # was 1,108 LoC
│   │   ├── __init__.py
│   │   ├── cache.py            (~80 LoC)  ← 3 cache util fns
│   │   ├── queries.py          (~300 LoC)
│   │   ├── fitter.py           (~300 LoC) ← actual training calls
│   │   └── state.py            (~450 LoC)
│   └── (기존 single-file states 그대로)
│
├── ml/pipeline/                # was 1,659 LoC single file
│   ├── __init__.py
│   ├── metadata.py             (~60 LoC)
│   ├── preprocessing.py        (~120 LoC)
│   ├── features.py             (~35 LoC)
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── base.py             (~25 LoC)
│   │   ├── autoarima.py        (~380 LoC)
│   │   ├── prophet.py          (~270 LoC)
│   │   └── xgboost.py          (~385 LoC)
│   ├── registry.py             (~40 LoC)
│   └── training.py             (~290 LoC)
│
└── ai_engine/agents/           # was 1,097 LoC
    ├── __init__.py
    ├── context.py              (~30 LoC)
    ├── base.py                 (~20 LoC)
    ├── research.py             (~445 LoC) ← 여전히 크지만 단일 책임
    ├── analysis.py             (~135 LoC)
    ├── review.py               (~130 LoC)
    └── orchestrator.py         (~335 LoC)
```

### 3.2 1,000+ LoC 파일 변화

| Before | LoC | After (largest sub-module) | LoC |
|---|---|---|---|
| dashboard.py | 1,826 | dashboard/state.py | ~700 |
| forecast_player_state.py | 1,668 | forecast_player/state.py | ~600 |
| training_state.py | 1,108 | training/state.py | ~450 |
| pipeline_v2_hybrid.py | 1,659 | plugins/xgboost.py | ~385 |
| enhanced_agent_orchestrator.py | 1,097 | agents/research.py | ~445 |

✅ Stage 4 완료 후 **1,000+ LoC 파일 0개** (목표 AC1 달성).
⚠️ research.py(445), xgboost.py(385) 등은 여전히 큰데, 단일 책임이라 더 쪼개면 응집성 깨짐 → 허용.

---

## 4. Implementation Order

**가장 작은 monolith부터 — 패턴 검증 + 위험 분산.**

### Sprint 1 (Day 1): 패턴 확립
1. **training_state.py (1,108 LoC)** ← 가장 작은 Reflex State monolith
   - utility 함수 3개를 cache.py로 분리
   - DB 쿼리 메서드를 queries.py로 분리
   - 학습 실행 메서드를 fitter.py로 분리
   - 4-way split 패턴 확립
   - **검증 게이트**: training_wizard 페이지 정상 부팅

### Sprint 2 (Day 2): ML pipeline (state 아님, 더 쉬움)
2. **ml/pipeline_v2_hybrid.py (1,659 LoC)** ← multi-class, 분할 가장 단순
   - 클래스별로 파일 split (P2 패턴)
   - `from edgeex_app.ml.pipeline_v2_hybrid import X` 호환성 위해 `ml/pipeline_v2_hybrid.py` 를 re-export shim으로 유지 (또는 import 경로 업데이트)
   - **검증**: training_state.fitter / forecast_scheduler 동작 확인

### Sprint 3 (Day 3): 큰 State 둘
3. **forecast_player_state.py (1,668 LoC)** — P1 패턴 적용
4. **dashboard.py (1,826 LoC)** — P1 패턴 적용
5. **enhanced_agent_orchestrator.py (1,097 LoC)** — P2 패턴 (시간 남으면)

---

## 5. Reflex State Split — 구체 패턴

### 5.1 비즈니스 로직 분리 원칙

State 클래스에 남길 것:
- ✅ State variables (`rx.var`, computed properties)
- ✅ `@rx.event` 데코레이터 메서드 (Reflex가 추적해야 함)
- ✅ `@rx.var` computed (state에 종속)

State에서 뺄 것:
- ❌ 순수 데이터 변환 (pandas/dict 매핑) → `view_helpers.py`
- ❌ DB 쿼리 (asyncpg) → `queries.py`
- ❌ 포맷팅/계산 utility → `utils.py`
- ❌ 외부 시스템 호출 (model fitting, file IO) → `fitter.py` 등

### 5.2 self-mutation 패턴

State 메서드에서 self 변경이 필요할 때:

```python
# ❌ helper에서 state 변경 시도 (안 됨, Reflex가 reactivity 못 잡음)
async def fetch_and_set(state):
    state.data = await db_query()

# ✅ helper는 return만, state 메서드가 받아서 set
# state.py
@rx.event(background=True)
async def load(self):
    async with rx.lock():
        data = await fetch_sensor_window(get_pool(), self.window)
        self.data = data  # ← set은 State 클래스에서만
```

### 5.3 Error handling

```python
# queries.py
async def fetch_sensor_window(pool, window: str) -> list[dict]:
    """Pure async function. Raises DBError on failure."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(SQL, window)
    return [dict(r) for r in rows]

# state.py
@rx.event(background=True)
async def load(self):
    try:
        async with rx.lock():
            self.data = await fetch_sensor_window(get_pool(), self.window)
            self.error = ""
    except Exception as e:
        async with rx.lock():
            self.error = str(e)
            self.data = []
```

---

## 6. Validation Strategy

### 6.1 분할 전후 동작 동일성

각 sprint 끝 검증:
1. **Static**: `python -c "import ast; ast.parse(open(f).read())"` 모든 새 파일
2. **Import**: `python -c "from edgeex_app.states.dashboard import DashboardState"` (호환성)
3. **Build**: `docker compose -f docker-compose.local.yml build reflex-app`
4. **Runtime**: `docker compose up -d reflex-app && curl http://localhost:14001/_health` (Reflex backend ping)
5. **UI smoke**: 분할 대상 페이지 (/, /forecast, /training-wizard 등) HTTP 200 + 화면 보이기

### 6.2 분할 단위 commit

- 1 sprint = 1 file 분해 = 1 commit (큰 patch지만 의미상 atomic)
- 또는 sprint 안에서 sub-commit: helpers → queries → view_helpers → state (4 단계)

### 6.3 Rollback 절차

`git revert <commit>` 가능 — 단일 파일 → 패키지 디렉토리 전환이므로 revert도 깔끔 (single git rename + Edit set).

---

## 7. Risks & Mitigations

| 리스크 | 확률 | 영향 | 완화 |
|---|---|---|---|
| Reflex State 분리 패턴이 reactivity 깨뜨림 | 중 | 높음 | training_state(가장 작음)로 PoC 후 dashboard/forecast 적용. self.* mutation은 반드시 @rx.event 안에서만. |
| `from edgeex_app.states.dashboard import DashboardState` 호환성 깨짐 | 낮음 | 높음 | `__init__.py`에서 명시 re-export. import 경로 변경 시 grep으로 모든 호출 site 일괄 업데이트. |
| ml/pipeline 분할 후 statsforecast Plugin이 importlib 발견 못 함 | 낮음 | 중 | `model_registry.pickle_data` 가 plugin 객체를 unpickle 할 때 class 위치 import path 변경 영향. Shim file로 backward import 유지. |
| 분할 작업 중 stale cache (Reflex의 .web/, .states/) 이상 동작 | 중 | 낮 | 각 sprint 시작 시 `.web/`, `.states/` 삭제 후 reflex run. |
| 메서드 의존성 추적 누락으로 NameError | 중 | 중 | 분할 후 즉시 `docker compose build` + import test. 깨지면 revert. |

---

## 8. Acceptance Criteria (Stage 4)

- [AC4-1] 1,000+ LoC 파일 = 0
- [AC4-2] 분할된 파일 모두 ≤ 500 LoC (research.py, xgboost.py 같은 단일 책임 예외 허용)
- [AC4-3] `python -c "from edgeex_app.states.dashboard import DashboardState"` 외 모든 기존 import 경로 동작
- [AC4-4] `docker compose build reflex-app` 성공
- [AC4-5] 분할 대상 페이지 (/, /forecast, /training-wizard, /model-performance) 정상 부팅 + 데이터 로드
- [AC4-6] git log: sprint 단위 atomic commit (5 또는 4 commits)

---

## 9. Open Questions

1. **OQ4-1**: `pipeline_v2_hybrid` 라는 파일명 자체가 v1/v2 흔적. Stage 4에서 `ml/pipeline/` 패키지로 rename하면 stale `pipeline_v2_hybrid.py` 가 어딘가 import되는 곳 있는지 검색 필요.
2. **OQ4-2**: `ForecastPlayerState(BaseState)` — `BaseState` 가 어디서 import되는지, 추상화 패턴 명확한지 확인. Stage 6 BaseState 통일 시 영향.
3. **OQ4-3**: Reflex 0.8.16의 `rx.lock()` 사용 패턴 — 분할 후 helper async 함수 안에서 lock 잡으면 안 됨 (State 메서드에서만). 모든 분할 시 검증.
4. **OQ4-4**: ai_engine/agents/ — 현재 사용처 (/ai 라우트는 Stage 1에서 제거됨). 정말 살아있는 코드인지 별도 검토. Dead라면 Stage 4 분해 대신 Stage 2식 통째 삭제.
5. **OQ4-5**: states/dashboard/ 분할 후 view_helpers.py 와 edgeex_app/views/ (이미 존재) 의 책임 경계.

---

## 10. References

- Plan: `docs/01-plan/features/rpi-refactor-stage2-7.plan.md` §4 Stage 4
- Refactor proposal: `reports/refactor_proposal_2026-05-19.html`
- Current state: 8 commits on `refactor/rpi-baseline-sync` branch (e397d8f...b52ec6b)
- 1000+ LoC inventory: Stage 1+2+3.5 결과 `find edgeex_app -name "*.py" -exec wc -l {} \;`

---

*Generated 2026-05-19 by Claude Opus 4.7 · PDCA Design template · Stage 4 monolith split blueprint*
