# Stage 4-1 Extraction Prompt — training_state refactor

> **Paste this entire file into a fresh local Claude Code session.**
> Working directory must be the project root containing `edgeex_app/`.

## Context (read first, don't re-derive)

- Source file: `edgeex_app/states/training_state/state.py` (1,077 LoC currently)
- Analysis report: `reports/deep1_analysis_2026-05-20.html` (commit `b6c1944`)
- Branch: `refactor/rpi-baseline-sync` (do NOT switch)
- Last commit: `b6c1944 deep(stage-4-1): PARTIAL — analysis done, extraction pending user confirm`

User has answered the 4 questions in the deep-1 report. **Locked decisions** (don't re-prompt the user on these):

| # | Decision | Choice |
|---|----------|--------|
| Q1 | Extraction depth | **B** — LOW + MED + HIGH **partial**. yield flow stays in `state.py`. |
| Q2 | Pipeline builder file | **A** — Create `pipeline_builder.py` with builder fn |
| Q3 | Commit shape | **B** — 4 sub-commits: 4-1a, 4-1b, 4-1c, 4-1d |
| Q4 | Yield handling | **A** — `progress_callback` async fn passed into builder |

## Acceptance criteria (do not ship unless all green)

| AC | Target | How to verify |
|----|--------|---------------|
| AC-1 | `training_state/state.py` ≤ 600 LoC | `wc -l edgeex_app/states/training_state/state.py` |
| AC-2 | All 7 external `from edgeex_app.states.training_state import …` sites unchanged | `grep -rn "from edgeex_app.states.training_state" edgeex_app/` then verify each still resolves |
| AC-3 | Docker build clean | `docker compose -f docker-compose.dev.yml build` no errors |
| AC-4 | `/training-wizard` route returns 200 + renders | After build: `curl -s -o /dev/null -w "%{http_code}" http://localhost:14000/training-wizard` |

## File layout to produce

```
edgeex_app/states/training_state/
├── __init__.py           # unchanged (23 lines, public API)
├── state.py              # ~600 LoC after extraction (target)
├── cache.py              # unchanged (existing)
├── queries.py            # NEW ~180L — async DB query helpers (4 LOW-risk methods)
├── view_helpers.py       # NEW ~170L — pure data transforms (save_model splits)
├── validators.py         # NEW ~30L  — input validation (MED-risk: create_feature_config)
└── pipeline_builder.py   # NEW ~100L — TrainingPipelineV2 builder (HIGH partial: from start_training)
```

## Execution order (Steps 5–8 from deep-1 report)

### Step 5 — Write the 4 new files

Order: `queries.py` → `validators.py` → `view_helpers.py` → `pipeline_builder.py`.

For each new file:
1. Identify the source block in `state.py` from the deep-1 analysis report.
2. Extract as **pure functions** (no `self.*` access). State methods will call these.
3. **CRITICAL for `pipeline_builder.py`** (Q4=A pattern):
   ```python
   # pipeline_builder.py
   from typing import Awaitable, Callable, Optional

   ProgressCallback = Callable[[str, int], Awaitable[None]]
   # signature: async def cb(status_msg: str, progress_pct: int) -> None

   async def build_training_pipeline(
       config: dict,
       progress_cb: Optional[ProgressCallback] = None,
   ) -> "TrainingPipelineV2":
       if progress_cb:
           await progress_cb("Initializing pipeline", 10)
       # ... build steps ...
       if progress_cb:
           await progress_cb("Pipeline ready", 100)
       return pipeline
   ```
   Then in `state.py`:
   ```python
   async def start_training(self):
       async def _on_progress(msg: str, pct: int):
           async with self:
               self.status = msg
               self.progress = pct
           yield  # preserve the yield flow at state-method level
       pipeline = await build_training_pipeline(self.config, _on_progress)
       # ... rest of start_training stays in state.py
   ```
   The yield stays where it always was — the builder just signals via callback.

### Step 6 — Rewrite `state.py`

- Replace each extracted block with a call to the new module.
- Keep `@rx.event` decorators, yields, and `async with self:` blocks IN `state.py`.
- Keep `@rx.var` properties IN `state.py`.
- Keep all 8 simple setters IN `state.py`.
- For `save_model`: keep ORM session calls in `state.py`, but extract the ~50L `pipeline_config` build + datetime parsing into `view_helpers.py`. Pass the session object only when strictly necessary (prefer returning data, letting `state.py` do the ORM write).

### Step 7 — Syntax + import verification

```powershell
python -m py_compile edgeex_app/states/training_state/state.py
python -m py_compile edgeex_app/states/training_state/queries.py
python -m py_compile edgeex_app/states/training_state/view_helpers.py
python -m py_compile edgeex_app/states/training_state/validators.py
python -m py_compile edgeex_app/states/training_state/pipeline_builder.py
python -c "from edgeex_app.states.training_state import *"
```
All five must compile and the wildcard import must succeed.

### Step 8 — Sub-commits (Q3=B shape)

**Important — never run Reflex on Windows host** (memory `feedback_no_host_reflex_zombie`). Verification = docker only.

Commit-by-commit:

#### 4-1a — queries.py extraction
```
git add edgeex_app/states/training_state/queries.py edgeex_app/states/training_state/state.py
git commit -m "deep(stage-4-1a): PARTIAL — extract queries.py (4 LOW methods)

- queries.py: async DB helpers extracted from state.py
- state.py: 4 LOW-risk methods now delegate to queries.py
- LoC: state.py 1077 → ~950"
docker compose -f docker-compose.dev.yml build
# verify build clean before next commit
```

#### 4-1b — validators.py + create_feature_config refactor
```
git add edgeex_app/states/training_state/validators.py edgeex_app/states/training_state/state.py
git commit -m "deep(stage-4-1b): PARTIAL — validators.py + create_feature_config refactor

- validators.py: input validation extracted
- create_feature_config (MED-risk) split into pure helpers + state shim
- LoC: state.py ~950 → ~900"
docker compose -f docker-compose.dev.yml build
```

#### 4-1c — view_helpers.py for save_model
```
git add edgeex_app/states/training_state/view_helpers.py edgeex_app/states/training_state/state.py
git commit -m "deep(stage-4-1c): PARTIAL — view_helpers.py for save_model

- view_helpers.py: pipeline_config build + datetime parsing extracted
- save_model: ORM session calls stay in state.py, data prep delegated
- LoC: state.py ~900 → ~700"
docker compose -f docker-compose.dev.yml build
```

#### 4-1d — pipeline_builder.py + start_training refactor (FINAL)
```
git add edgeex_app/states/training_state/pipeline_builder.py edgeex_app/states/training_state/state.py
git commit -m "deep(stage-4-1d): PASS — pipeline_builder.py + start_training refactor

- pipeline_builder.py: TrainingPipelineV2 builder with progress_callback pattern
- start_training: pipeline build delegated, yield flow + 30 self.* mutations stay in state.py
- LoC: state.py ~700 → ~600 (AC-1 target met)

Acceptance criteria:
- AC-1 state.py ≤ 600 LoC ✓
- AC-2 7 external imports unchanged ✓
- AC-3 docker build clean ✓
- AC-4 /training-wizard 200 ✓

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

Then final integration verification:
```powershell
docker compose -f docker-compose.dev.yml up -d
$env:PYTHONUTF8 = "1"
Start-Sleep 30  # let reflex compile inside container
curl.exe -s -o $null -w "%{http_code}`n" http://localhost:14000/training-wizard
# must print: 200
docker compose -f docker-compose.dev.yml logs --tail=50 reflex
# no tracebacks, no import errors
```

## What to write to HANDOFF.md on completion

Append a new entry under "Round 4":
```markdown
## Round 4 — Stage 4-1 extraction (2026-05-20)

**training_state/state.py 1077 → ~600 LoC. 4 sub-commits 4-1a/b/c/d. All AC pass.**

- queries.py / view_helpers.py / validators.py / pipeline_builder.py 신규
- start_training yield 흐름 보존 (progress_callback 패턴)
- save_model ORM 호출은 state.py 유지
- Docker build clean, /training-wizard 200
- Branch: refactor/rpi-baseline-sync (unmerged — next step is Stage 5)
```

## Things NOT to do

- ❌ Don't run `python -m reflex run` on Windows host (creates zombie TCP sockets — `feedback_no_host_reflex_zombie`)
- ❌ Don't merge to master in this session; stay on `refactor/rpi-baseline-sync`
- ❌ Don't switch `__init__.py` public exports — keep AC-2 invariant
- ❌ Don't extract `start_training`'s yield blocks (Q4=A: yields STAY in state.py)
- ❌ Don't expose SQLAlchemy session objects across module boundaries — keep ORM writes in state.py
- ❌ Don't squash the 4 sub-commits — bisect-friendly history matters here

## Output to user on completion

Generate `reports/extract_stage-4-1_2026-05-20.html` (HTML, not markdown — memory `feedback_pdca_html_output` + `feedback_prefer_html_report`):
- Executive Summary table (Problem / Solution / Function UX Effect / Core Value)
- Before/after LoC table per file
- 4 sub-commit SHAs
- AC verification matrix (✓/✗ per AC-1..AC-4)
- Docker build + route check evidence

Open the report in browser when done.
