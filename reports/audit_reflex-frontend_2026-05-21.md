# KSys IoT — Reflex Frontend/State Architecture Audit
**Date**: 2026-05-27 | **Reflex**: 0.8.x | **Auditor**: bkit-frontend-architect

---

## 1. State Class Organization

### F-1.1 · Dual BaseState — two conflicting base classes in production
**File**: `ksys_app/states/base.py:10` vs `ksys_app/states/base_state.py:12`

```python
# base.py — uses raw pool (db.q), has toggle_auto_refresh, clear_error
class BaseState(rx.State):
    is_loading: bool = False
    error: str = ""
    auto_refresh_enabled: bool = False
    ...

# base_state.py — uses get_async_session ORM, has _polling_active
class BaseState(rx.State):
    _polling_active: bool = False
    loading: bool = False
    error_message: str = ""
    ...
```

**Problem**: Two classes named `BaseState`, both imported by different state files. States that import from `base_state.py` (`DashboardRealtimeState`, `TagHierarchyState`, `TrainingWizardStateEnhanced`) use the ORM session version; states that inherit directly from `rx.State` (`AlarmState`, `AlarmRTState`, `AIState`, `CommunicationState`) inherit neither — UI-level common patterns (sidebar, theme) are duplicated or missing. Name collision also causes silent import shadowing.

**Reflex 0.8 idiomatic fix**: Merge into a single `AppState(rx.State)` with `sidebar_collapsed`, `theme_mode`, and one polling pattern. Make domain states inherit from it.

---

### F-1.2 · DashboardState monolith — 40+ state vars in one class
**File**: `ksys_app/states/dashboard/state.py:39–145`

```python
class DashboardState(rx.State):
    tag_name: Optional[str] = None
    window: str = "5 min"
    series: List[Dict[str, Any]] = []
    features: List[Dict[str, Any]] = []
    latest: List[Dict[str, Any]] = []
    indicators: List[Dict[str, Any]] = []
    kpi_rows: List[Dict[str, Any]] = []
    mini_chart_data: Dict[str, List[Dict[str, Any]]] = {}
    show_avg: bool = True
    show_min: bool = True
    # ... ~25 more vars ...
    realtime_data: Dict[str, List[Dict[str, Any]]] = {}
    _realtime_loop_id: Optional[str] = None
    active_alarms: List[Dict[str, Any]] = []
    detail_modal_open: bool = False
    selected_sensor_data: Dict[str, Any] = {}
    sidebar_collapsed: bool = False
```

**Problem**: Mixes chart data, KPI tiles, tech indicators, real-time loop control, alarm state, modal state, and sidebar state in one class. Every state mutation (e.g. toggling a checkbox) re-serializes the entire state including heavy `List[Dict]` chart blobs. 40+ vars is above the 30-var smell threshold.

**Reflex 0.8 idiomatic fix**: Extract `ChartVisibilityState`, `RealtimeLoopState`, and `AlarmSummaryState` as sibling substates. Dashboard page composes from all three.

---

### F-1.3 · Four-level inheritance chain for TrainingWizardStateEnhanced
**File**: `ksys_app/states/training_wizard_state_enhanced.py:15`

```python
class TrainingWizardStateEnhanced(TrainingWizardState, TagHierarchyState):
    # TrainingWizardState -> TrainingState(rx.State)
    # TagHierarchyState  -> BaseState(base_state.py) -> rx.State
```

**Problem**: `TrainingWizardStateEnhanced` sits at depth 4 from `rx.State` via multiple inheritance, creating an MRO that Reflex's serialization resolves left-to-right. `tag_search_query` exists in **both** `TrainingWizardStateEnhanced` (line 19) and `TagHierarchyState` (line 34) — silent shadowing. Reflex substates are designed for vertical fan-out, not mixin-style horizontal mixing.

**Reflex 0.8 idiomatic fix**: Make `TagHierarchyState` a standalone substate (not base-mixed). Page reads both states independently via `TagHierarchyState.filtered_tags` and `TrainingWizardState.selected_tag`.

---

### F-1.4 · `@rx.var` returning new mutable dicts on every call
**File**: `ksys_app/states/training_wizard_state.py:36`

```python
@rx.var
def validation_feasibility(self) -> dict:
    if self.forecast_interval_minutes <= 0:
        return {
            'is_valid': False,
            'test_size': 0,
            # ... 6 more keys
        }
```

**Problem**: Returns a new `dict` literal on every recomputation. Reflex serializes `@rx.var` results to the frontend; when the dict is structurally equal but a new object, some Reflex 0.8 builds still re-send the full delta. Use `cache=True` for expensive computed vars that return complex types.

**Reflex 0.8 idiomatic fix**:
```python
@rx.var(cache=True)
def validation_feasibility(self) -> dict:
    ...
```
Apply similarly to `forecast_chart_data`, `combined_forecast_chart_data`, `validation_table_data` (all in `training_wizard_state.py`).

---

## 2. Event Handler Patterns

### F-2.1 · Long-running DB work inside `async with self:` state lock
**File**: `ksys_app/states/base.py:78–98`

```python
@rx.event(background=True)
async def start_auto_refresh(self):
    async with self:
        if self._refresh_task_running:
            return
        self._refresh_task_running = True

    while True:
        async with self:
            if not self.auto_refresh_enabled:
                ...
        if hasattr(self, 'refresh_data'):
            await self.refresh_data()  # DB query runs OUTSIDE lock — correct
        yield
```

**Assessment**: This base pattern is actually correct — DB call is outside `async with self:`. However, in `alarm_rt_state.py` (lines 116–130) and `alarm_state.py`, state writes (`self.all_sensors = ...`) happen inside `async with self:` after large list construction — lock is held only for the assignment, which is fine.

**Actual smell**: `base_state.py` line 57 calls `self.refresh_data()` without `await` inside a background task (`asyncio.wait_for` wraps the call, which is fine for a coroutine but `refresh_data` is decorated `@rx.event(background=True)` — calling it as `await coro()` skips Reflex's event dispatch and yields nothing to the frontend).

---

### F-2.2 · Generator-style `yield` mixed with `async with self: yield` pattern inconsistently
**File**: `ksys_app/states/dashboard_realtime.py:68–117`

```python
@rx.event(background=True)
async def start_streaming(self):
    async with self:
        self.is_streaming = True
        self.last_update = "Initializing..."
        yield  # yields inside lock — correct for Reflex 0.8

    # ...
    while self.is_streaming:
        await asyncio.sleep(self.update_interval)
        try:
            await asyncio.wait_for(self._fetch_data(), ...)
            yield  # bare yield OUTSIDE async with self — problematic
```

**Problem**: The bare `yield` at line 108 is outside `async with self:`. In Reflex 0.8 background tasks, yielding state updates must happen inside `async with self:` or via `yield EventSpec`. A bare yield here does not acquire the state lock, which means the UI update may race with `_fetch_data`'s own `async with self:` block.

**Reflex 0.8 idiomatic fix**:
```python
await asyncio.wait_for(self._fetch_data(), ...)
async with self:
    yield  # acquire lock before signalling UI
```

---

### F-2.3 · Function-internal imports in hot-path event handlers
**File**: `ksys_app/states/dashboard/state.py:1135–1136`, `ksys_app/states/training_wizard_state.py:163`

```python
@rx.event(background=True)
async def start_realtime(self):
    import time       # line 1135 — executed on every event call
    import uuid       # line 1136

@rx.event(background=True)
async def initialize_wizard(self):
    # ...
    from sqlalchemy import text   # line 163 — inside background event body
```

**Problem**: `import time` / `import uuid` are stdlib modules with trivial import cost but signal a sloppy pattern. The SQLAlchemy `from sqlalchemy import text` inside `initialize_wizard` runs every time the event fires. Move all imports to module top-level.

---

### F-2.4 · `print()` used as logging in production state event handlers
**File**: `ksys_app/states/dashboard/state.py:1144, 1149, 1156, 1159, 1173, 1177`

```python
print(f"🚫 {current_time} - 싱글톤 보호: 실시간 루프가 이미 실행 중 (ID: {self._realtime_loop_id})")
print(f"⚠️ {current_time} - 실시간 모드가 비활성화되어 루프 시작 취소")
```

**Problem**: 25 `print()` calls in `dashboard/state.py` alone (987 total across the codebase in non-test code), plus 45 in state files. `print()` bypasses Reflex's `console` log level control (`LogLevel.DEBUG` set in rxconfig), floods server stdout, and cannot be silenced in production without code changes.

**Reflex 0.8 idiomatic fix**:
```python
from reflex.utils import console
console.debug(f"Singleton guard: realtime loop already running (ID: {self._realtime_loop_id})")
```
`console` respects `loglevel=LogLevel.INFO` in production config.

---

### F-2.5 · `stop_polling` / `stop_streaming` not decorated with `@rx.event`
**File**: `ksys_app/states/base_state.py:74` and `ksys_app/states/dashboard_realtime.py:119`

```python
async def stop_polling(self):     # missing @rx.event
    async with self:
        self._polling_active = False

async def stop_streaming(self):   # missing @rx.event
    async with self:
        self.is_streaming = False
```

**Problem**: Methods that mutate state must be decorated with `@rx.event` in Reflex 0.8 to be safely dispatchable from the frontend or from other events. Without the decorator these cannot be called from component `on_click` or `on_unmount` handlers; callers must use the class-level reference as an event spec, which is inconsistent.

---

## 3. Component Composition

### F-3.1 · Python dict-key access on `rx.foreach` item (common Sonnet 4.0-era bug)
**File**: `ksys_app/pages/alarms.py:88, 111, 113`

```python
def alarm_card(alarm: Dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.flex(
                level_badge(alarm["level"], alarm["level_name"]),  # dict access
                rx.text(alarm["triggered_at_short"], ...),         # dict access
            ),
            rx.text(alarm["message"], ...),
            rx.flex(
                rx.hstack(
                    rx.badge(alarm["tag_name"], ...),
                    rx.text(f"{alarm['value']}{alarm['unit']}", ...),
```

**Problem**: `alarm_card` is called via `rx.foreach(AlarmsState.paginated_alarms, alarm_card)`. Inside `rx.foreach`, each item is a `Var[Dict]`, not a plain Python dict. Accessing `alarm["level"]` with Python `[]` notation raises a `VarTypeError` at runtime or silently returns a static Var pointing to the wrong index. Must use `alarm["level"]` through Reflex Var subscript (which does work for `Dict` Vars in 0.8) — but calling a pure Python helper like `level_badge(alarm["level"], alarm["level_name"])` passes a `Var` object as a Python int to `color_map.get(level, "gray")`, which will never match and always return "gray". This is a silent correctness bug.

**Reflex 0.8 idiomatic fix**: `level_badge` should accept `Var` types and use `rx.cond` for branching, or the color should be pre-computed in state as a string field in each alarm dict.

---

### F-3.2 · Hardcoded hex color strings as magic values across components
**Files**: `ksys_app/components/layout.py:74,80`, `ksys_app/components/sensor_card_enhanced.py:68,70,72,117,118,138,183`, `ksys_app/pages/alarms.py:93,105,113,115,162,164`

```python
# layout.py
color="#3b82f6" if is_active else "#6b7280",  # blue-500 / gray-500

# sensor_card_enhanced.py
return "#3b82f6"  # blue
return "#f59e0b"  # amber
return "#ef4444"  # red

# alarms.py
color="#6b7280"   # gray-500 — repeated 8+ times
color="#111827"   # gray-900 — repeated 10+ times
```

**Problem**: The same color hex appears 20+ times across layout, sensor card, and alarms page. `rxconfig.py` already sets up `TailwindV3Plugin` with a custom theme (status colors, slate-850). None of the components use those tokens. If the amber warning color needs to change (e.g., accessibility contrast), it requires a grep-and-replace across 8 files.

**Reflex 0.8 idiomatic fix**: Centralize in `ksys_app/styles/design_tokens.py` (file already exists) and reference via Tailwind classes or a `COLOR` constant dict imported by all components.

---

### F-3.3 · `rx.cond` chains instead of Tailwind variant maps — unreadable and error-prone
**File**: `ksys_app/pages/alarms.py:155–166`

```python
rx.badge(
    rx.cond(sensor["status"] == 0, "NORMAL",
        rx.cond(sensor["status"] == 1, "WARNING", "CRITICAL")),
    color_scheme=rx.cond(sensor["status"] == 0, "green",
        rx.cond(sensor["status"] == 1, "amber", "red")),
    ...
)
```

**Problem**: Deeply nested `rx.cond` chains are the correct Reflex-reactive pattern (not Python `if`), so reactivity is intact. However, the pattern is repeated in at least 4 component functions for the same status→color mapping. This should be a helper or a pre-computed string field in state.

**Reflex 0.8 idiomatic fix**: Pre-compute `status_label: str` and `status_color: str` in `DashboardRealtimeState.formatted_sensors` (already partially done) and access directly — no `rx.cond` chain needed.

---

### F-3.4 · `ksys_app/pages/alarms.py` — 400+ LoC god-component file
Checked: `alarms.py` contains `isa_level_badge`, `level_badge`, `stat_tile`, `alarm_card`, `active_alarms_view`, `history_alarms_view`, and the full page function inline. No dedicated component file for alarm-specific renderers. Similar pattern in `trend_enhanced_v2.py` (30+ `rx.cond` / `rx.foreach` calls, full page in one file).

---

### F-3.5 · Inline `lambda` event handlers in `rx.foreach` callbacks
**File**: `ksys_app/pages/alarms.py:128, 198`

```python
on_click=lambda: AlarmsState.acknowledge_alarm(alarm["event_id"]),
```

**Problem**: Lambda capturing a `rx.foreach` loop variable (`alarm["event_id"]`) works in Reflex 0.8 if `alarm` is a `Var` and `alarm["event_id"]` produces an `EventSpec`. However, the lambda notation bypasses Reflex's type-checking of event args and may silently pass a `Var[str]` where a `str` is expected, causing serialization issues. Confirmed pattern — used in 2 places.

**Reflex 0.8 idiomatic fix**: Use partial application syntax directly:
```python
on_click=AlarmsState.acknowledge_alarm(alarm["event_id"]),
```

---

## 4. Async DB Patterns

### F-4.1 · Custom `get_async_session` shim instead of `rx.asession()`
**File**: `ksys_app/db_orm.py:1–60`

```python
# db_orm.py — custom async engine factory
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
...
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    ...
```

**Problem**: Reflex 0.8 exposes `rx.asession()` (see `C:\dev\venv-ksys\Lib\site-packages\reflex\model.py:611`) which returns a managed `AsyncSession` with the same lazy-init pattern, configured via `rx.Config(async_db_url=...)`. The project bypasses this entirely in favor of a custom shim with its own pool (`NullPool` by default, `AsyncAdaptedQueuePool` via env var).

**Assessment**: The custom shim is actually well-engineered — it handles `asyncpg`-specific URL normalization, pool configuration, SSL, and `statement_timeout`. However it means `rxconfig.py` does not declare `async_db_url`, so Reflex's own DB migration/model tooling (`rx.Model`, `rx.alembic`) is not connected. This is a deliberate architectural choice but should be documented as such.

**Verdict**: Not a bug — acceptable for a TimescaleDB + asyncpg setup that needs fine-grained pool control. Flag for new contributors.

---

### F-4.2 · Raw SQL in state event handlers bypassing service layer
**File**: `ksys_app/states/alarm_rt_state.py:63–86`, `ksys_app/states/alarm_state.py:63–100`

```python
@rx.event(background=True)
async def load_sensor_status(self):
    query = """
        SELECT l.tag_name, ROUND(l.value::numeric, 2) as value, ...
        FROM influx_latest l
        LEFT JOIN influx_qc_rule q ON l.tag_name = q.tag_name
        ...
    """
    rows = await q(query, ())
```

**Problem**: `AlarmRTState` and `AlarmState` bypass the service layer and call raw SQL via `from ..db import q` directly in event handlers. `DashboardRealtimeState` (the newer, refactored state) uses `SensorService` correctly. This inconsistency means alarm-related SQL has no centralized testing surface.

---

## 5. rxconfig.py Assessment

**File**: `rxconfig.py`

```python
config = rx.Config(
    app_name="ksys_app",
    loglevel=LogLevel.DEBUG,     # DEBUG in production docker — noisy
    show_built_with_reflex=False,
    frontend_packages=[],
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV3Plugin(config={...}),
    ],
    frontend_port=14000,
    backend_port=14001,
    backend_host="0.0.0.0",
)
```

**Findings**:

| Item | Status | Detail |
|------|--------|--------|
| `loglevel=LogLevel.DEBUG` | Smell | Production containers log debug output; should be `LogLevel.INFO` with DEBUG only in dev |
| `async_db_url` absent | Intentional | Custom `db_orm.py` shim handles this (see F-4.1) |
| `telemetry_enabled` absent | Default=True | Sends usage telemetry to Reflex team; set `telemetry_enabled=False` for an air-gapped IoT deployment |
| `cors_allowed_origins` absent | Default="*" | Open CORS on port 14001 backend — acceptable on LAN, risky if port is forwarded |
| `TailwindV3Plugin` configured | Good | Custom status colors and Inter font defined — but not used by components (see F-3.2) |
| `SitemapPlugin` present | Low value | A SCADA IoT app behind a firewall has no SEO use for a sitemap |

---

## 6. "Sonnet 4.0 Era" Anti-Patterns

### F-6.1 · `Dict[str, Any]` / `dict` as default var type for all complex state
97 occurrences of `Dict[str, Any]` across 16 state files (grep result). Specific examples:

```python
# training_state/state.py:66–82
result_metadata: dict = {}
model_diagnostics: dict = {}
preprocessing_stats: dict = {}
feature_engineering_stats: dict = {}
evaluation_metrics: dict = {}
residuals_analysis: dict = {}
saved_model_info: dict = {}
```

Seven `dict` vars holding different domain shapes with no TypedDict definition. The `@rx.var` accessors like `mae_value`, `aic_value` defensively call `.get()` on these dicts — which is the tell-tale sign these should be typed models or at least TypedDict.

---

### F-6.2 · `Message(Dict)` class — invalid Python pattern
**File**: `ksys_app/states/ai_state.py:15–19`

```python
class Message(Dict):
    """Message structure for chat"""
    text: str
    is_ai: bool
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
```

**Problem**: `class Message(Dict)` is not a valid Python type definition. `Dict` is a generic alias from `typing`, not a base class. This class would be equivalent to a bare `class Message(dict)` at runtime with no type enforcement. The field annotations (`text: str`) are class-level vars, not instance attributes. Actual `messages` state var stores `List[Dict[str, Any]]` — this class is unused as a type enforcer.

**Reflex 0.8 idiomatic fix**: Use `TypedDict` or a Pydantic `BaseModel`:
```python
from typing import TypedDict
class Message(TypedDict):
    text: str
    is_ai: bool
    timestamp: str
```

---

### F-6.3 · `@rx.var` computing pandas operations on every recomputation
**File**: `ksys_app/states/communication_state.py:66–157`

```python
@rx.var
def overall_success_rate(self) -> float:
    if not self._df_hourly:
        return 0.0
    df = pd.DataFrame(self._df_hourly)   # allocates new DataFrame every call
    df['record_count'] = pd.to_numeric(df['record_count'], errors='coerce')
    ...

@rx.var
def total_records(self) -> int:
    df = pd.DataFrame(self._df_hourly)   # second DataFrame allocation
    ...

@rx.var
def heatmap_matrix(self) -> List[List[float]]:
    df = pd.DataFrame(self._df_hourly)   # third DataFrame allocation
    pivot = df.pivot_table(...)
    ...
```

**Problem**: `_df_hourly` list is re-wrapped in a `pd.DataFrame` three separate times per state update cycle (three different `@rx.var` properties each creating their own DataFrame). In Reflex 0.8, `@rx.var` properties recompute whenever any state var changes. During a polling loop, this allocates 3+ DataFrames on every poll tick.

**Reflex 0.8 idiomatic fix**: Add `@rx.var(cache=True)` to all three, or pre-compute aggregates in the event handler and store them as plain state vars (`overall_success_rate: float`, `total_records: int`) updated once at fetch time.

---

### F-6.4 · Emoji characters in `console.log` / `print` in production state code
**File**: `ksys_app/states/dashboard/state.py:1159`, `ksys_app/states/trend_state_enhanced.py:57`, multiple

```python
console.log("🔄 TrendStateEnhanced.load() called")
print(f"🚀 {start_time} - 실시간 모드 시작 [ID:{loop_id}]")
print("=" * 80)
print("🚀 Starting Forecasting Schedulers from State...")
```

**Problem**: Emoji in log strings breaks Korean Windows deployments unless `PYTHONUTF8=1` is set (known issue for this env per memory). Also, decorative separators (`"=" * 80`) and emoji tags signal development/prototype code that was never cleaned up for production.

---

## Top 5 Modernization Wins

| Rank | Finding | File(s) | UX/Perf Impact | Effort | Score |
|------|---------|---------|---------------|--------|-------|
| 1 | **F-6.3** — Add `cache=True` to 3 pandas `@rx.var` in `CommunicationState` | `communication_state.py:66–157` | High (eliminates 3x DataFrame allocation per poll tick) | 15 min | 9 |
| 2 | **F-2.4** — Replace 45 `print()` calls in states with `console.log/debug` | `dashboard/state.py`, `alarm_rt_state.py`, 4 others | Medium (prod log hygiene, respects LogLevel) | 30 min | 8 |
| 3 | **F-1.1** — Merge dual `BaseState` and route all states through one base | `base.py` + `base_state.py` | Medium (eliminates inconsistent sidebar/theme behavior across pages) | 2h | 7 |
| 4 | **F-3.2** — Replace hardcoded hex strings with design token constants | `sensor_card_enhanced.py`, `layout.py`, `alarms.py` | Low/Medium (theme consistency, ~1 change propagates everywhere) | 1h | 7 |
| 5 | **F-2.2** — Fix bare `yield` outside `async with self:` in streaming loop | `dashboard_realtime.py:108` | High (prevents race condition in UI update during polling) | 10 min | 9 |

---

## Summary by Section

| Section | Findings | Severity |
|---------|----------|----------|
| State Organization | F-1.1 (dual base), F-1.2 (monolith 40+), F-1.3 (4-level inheritance), F-1.4 (mutable `@rx.var`) | Medium–High |
| Event Handlers | F-2.1 (assessed OK), F-2.2 (bare yield race), F-2.3 (hot-path imports), F-2.4 (print not console), F-2.5 (missing `@rx.event`) | Low–High |
| Components | F-3.1 (dict Var subscript silent bug), F-3.2 (magic hex), F-3.3 (`rx.cond` chains), F-3.4 (god files), F-3.5 (lambda capture) | Medium |
| DB Patterns | F-4.1 (custom shim — intentional), F-4.2 (raw SQL in state) | Low |
| rxconfig | DEBUG in prod, no `telemetry_enabled=False`, open CORS | Low–Medium |
| Sonnet 4.0 | F-6.1 (`dict` typing), F-6.2 (`Message(Dict)`), F-6.3 (pandas in `@rx.var`), F-6.4 (emoji logs) | Low–High |
