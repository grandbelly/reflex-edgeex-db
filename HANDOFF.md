## 2026-10-28 — ongoing mini SCADA / Reflex 0.10.1

Owner's full-template study/design is now documented: `docs/reflex_template_catalog.md` covers all 27 registered templates plus the repository-only dalle, with pinned sources and static inventory; `docs/mini_scada_component_layout_design.md` specifies six distinct layouts, component matching, data dependencies, interactions, partial/missing states and acceptance criteria; `docs/mini_scada_layout_board.html` is an offline six-menu design board, not a running SCADA or live-data screenshot. See `docs/template-study/inventory.json` for 359 Python-file fingerprints/definitions. No product UI acceptance or operating deployment is implied. Next implementation follows that design, starting with shared stock styling then real VQT trend/evidence. Preserve the uncommitted Company-style experiments until intentionally superseded.

Latest owner steering: study GitHub templates first; use stock_market_dashboard layout and stock_graph_app live chart; define distinct visualization purposes for each original menu before implementation. Read `docs/mini_scada_visualization_contract.md` and `docs/reflex_template_study.md`. PR#2 is a technical baseline with UI revision ongoing. Do not report the existing common tables as completed UX. Current Company-style edits in components/scada.py, views/scada_view.py, states/scada_state.py, assets/scada.css and rxconfig.py are uncommitted experiments, not the chosen stock template implementation. The isolated preview was stopped for these edits; XG5000/SimCore/502 and operating services remain untouched.

Owner: use Context7, latest Reflex, official template for the full mini SCADA. Branch `feat/mini-scada-data-contract`, base `pl/edge-monitor-candidate-20261027` dd958d7. Native six-route read-only profile is the new entry. See `docs/mini_scada_contract_plan.md` and `docs/reflex_template_source.md`.

Dedicated venv `C:/edgeex-it/cr277/refactor-venv010`, separate Reflex/Bun cache `C:/edgeex-it/cr277/reflex-cache010`, localhost preview3101. Operating Consumer/Redis/channels/installations/containers and Chrome9333 untouched. Health table remains absent in the upper DB; display partial failure, do not create schema. No registry/process bindings/collection plan/authorized ACK contract supplied yet. Production deployment is separate.

# Mini SCADA common-contract implementation — 2026-10-27

- Owner approved full review then continuation. Isolated `upper-refactor`, branch `feat/mini-scada-data-contract`, base dd958d7. Existing upper-web dirty files and 3100/8100 left untouched.
- Explicit edge_vqt read profile routes all six menus through a site-scoped read model. SQL read-only snapshot, partial optional-section errors, NULL/zero/quality/source-time semantics, bounded trends, one shared context/fixed-time mode. No inferred metadata/expected counts/PLC status. No ACK/control writes or in-app jobs.
- Dedicated existing test venv `upper-web/.venv` is read for dependencies; source/outputs are in this worktree and `C:/edgeex-it/cr277/refactor-*`. New 3101/8101 candidate binds localhost only. Existing running XG-SIM/Consumer/forwarder/containers/config remain untouched.
- 15 contract tests passed; four semantic mutants detected. Actual upper DB read: SY106 and 60-minute counts, Health missing reported separately, readonly on. Reflex compile passed after initializing the isolated .web directory. First compile failure (missing package.json) is preserved.
- Next: freeze source, browser checks on all six pages/fixed-time context, independent SQL parity, evidence/PR. NOT overall mini-SCADA completion or operational deployment. Future units: definition/version sync, process bindings, scheduled-slot completeness, long-term aggregates, authenticated ACK ownership, load/rollout.

# D-1027-20 엣지 웹 시연 인계 — 2026-10-27

- 엣지 전용 worktree: `C:/edgeex-it/cr277/upper-web`, 후보 `pl/edge-monitor-candidate-20261027`.
- URL `http://192.168.219.41:3100/edge-monitor`, backend `192.168.219.41:8100`; 오너 Orca peer `192.168.219.43`만 시연 방화벽 두 규칙으로 허용.
- 별도 `.venv`, AI·앱 내 Kafka Consumer 비활성. DSN은 기존 secrets에서 자식 환경에만 읽으며 DB 세션은 읽기 전용이다.
- 운영 Consumer는 `C:/edgeex-it/cr277/upper`의 `74b048e`, PID 30620/22576 그대로다. 그룹·수집·전달기·브로커는 변경하지 않았다.
- 실제 상위 DB `127.0.0.1:55432/postgres`: VQT·경보·SY 차트 조회 가능. **edgeex_health_latest 표 부재(42P01)**로 전체 시연 PASS가 아니다. 앱에 조회 실패를 표시한다. 스키마 생성은 하지 않았다.
- 런타임 로그 `C:/edgeex-it/cr277/web-runtime/`, 현재 상위 프로세스 PID 8144. 시연 종료 뒤 `C:/edgeex-it/cr277/stop-demo-firewall.ps1`로 이 과제의 두 규칙만 제거한다. 운전 Consumer는 정지하지 않는다.
- 엣지 영수증: `fable/receipts/acceptance/20261027T224126+0900__d1027-20-edge-monitor-demo/` (edgeex 저장소). 최종 후보 시험 4건, 화면/DB 관측 364개 불일치 0, backend WS 101. 오너 원격 브라우저 입회는 별도 확인한다.

# Session Handoff — 2026-05-18 (Round 3)

다음 Claude Code 세션에게 전달하는 작업 인계서. 이 폴더에서 새 세션 시작 시 가장 먼저 읽을 것.

---

## 🎯 Round 3 한 줄 요약 (가장 최근)

**`/agentic-pipeline forecast-scheduler-timeout-fix` 4-stage 완료 + master에 머지.** Karpathy 4-stage 시운전 끝. Alice(H5 DB timeout) + Bob(H2/H3 fake-async predict) + Charlie(H4/H7 timing + isolation) 세 패치가 master에 commit `6a9f989`, `52668e9`, `1f8f7fd`, `12f0914` 4건으로 안착. 9/9 unit 테스트 통과 (5.77s). worktree 4개 + branch 4개 + team config 정리 완료.

### 최종 결과 위치
- 종합 보고서: `agentic-runs/forecast-scheduler-timeout-fix/REPORT.md`
- Stage 2 합본: `agentic-runs/forecast-scheduler-timeout-fix/STAGE_2_REPORT.md`
- Stage 3 검증: `agentic-runs/forecast-scheduler-timeout-fix/wt/verifier/REPORT_verifier.md` (worktree 삭제됐지만 보고서 디렉터리는 남김)
- 이벤트 로그: `agentic-runs/forecast-scheduler-timeout-fix/events.jsonl` (49 events)

### 다음 세션이 알아야 할 것
1. **Agent Teams env var는 settings.json에 영구 등록됨** (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). 다음 세션 부팅 시 `Agent(team_name, name)` 호출 경로가 노출되면 진짜 Teams 패턴으로 동작 가능. 이번 세션에서는 `SendMessage`/`TeamCreate`/`TeamDelete`만 deferred로 보였고 spawn은 일반 subagent로 떨어졌음 — `REPORT.md` "Honest notes on Agent Teams integration" 참조.
2. **Forecast-scheduler 배포 시점에 env 변수 자동 적용** — `Dockerfile.scheduler`에 `USE_DB_POOLING=true`, `DB_COMMAND_TIMEOUT=30`, `DB_STATEMENT_TIMEOUT_MS=30000`, `FORECAST_PICKLE_LOAD_TIMEOUT=15.0`, `FORECAST_MODEL_PREDICT_TIMEOUT=45.0` 박혀 있음. Reflex 웹 이미지는 기존 default 그대로 (NullPool).
3. **로컬 풍도 코드 ↔ RPI 동기화 필요** — master는 풍도 폴더 기준. RPI(`/home/tion/deployment/20251030-rpi-finished/`)는 아직 patch 안 들어감. `scp`로 `edgeex_app/schedulers/forecast_scheduler.py`, `edgeex_app/db_orm.py`, `edgeex_app/schedulers/scheduler_manager.py`, `Dockerfile.scheduler` 4개 동기화 후 `docker compose up -d --build scheduler` 필요.
4. **남은 follow-up** (블로커 아님):
   - `save_predictions` 36-row INSERT 배치화 (Alice's note)
   - `README.md:97` "5-min intervals" 텍스트 갱신 (Charlie's note) — `/document-release`
   - 전용 ThreadPoolExecutor + env-var clamp (Verifier L1/L2)
5. **graphify --update는 아직 미실행** — 코드 변경분 그래프 반영하려면 다음 세션에서 `/graphify --update` (graphify-out/ 비어 있음, 첫 풀빌드부터 시작해야 함). 이번 세션에서 미수행. 시간/토큰 예산 큼 — 별도 세션 권장.

---

## Round 2 한 줄 요약 (배경)

**풍도 로컬 개발 환경 셋업 완료.** Docker Desktop 4.73.1 재설치 → DB 컨테이너 + ecoanp 복원 (294K rows 시계열 데이터) → Reflex 0.8.16 정상 실행 (frontend :14000, backend :14001).

---

## 🚀 다음 실행 방법 (단 5단계)

```powershell
# 1. Docker Desktop 켜져 있어야 함 (보통 자동 시작)
docker ps   # 응답 없으면 Docker Desktop UI 실행

# 2. DB 컨테이너 시작
cd C:\sync\00_ServerPC\reflex\reflex-rpi\reflex-rpi-local-deployment-poongdo
docker compose -f docker-compose.dev.yml up -d

# 3. DB 준비 확인 (5초 내 ready 됨)
docker exec edgeex-dev-db pg_isready -U postgres

# 4. Reflex 실행 — PYTHONUTF8 환경변수 필수!
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:TS_DSN = "postgresql://postgres:postgres@localhost:5432/ecoanp?sslmode=disable"
$env:POSTGRES_CONNECTION_STRING = "postgresql://postgres:postgres@localhost:5432/ecoanp?sslmode=disable"
$env:APP_ENV = "development"
C:\dev\venv-edgeex\Scripts\python.exe -m reflex run

# 5. 접속: http://localhost:14000 (frontend) / http://localhost:14001 (backend)
```

**Tip**: 매번 PYTHONUTF8 입력하기 귀찮으면 `C:\dev\venv-edgeex\Scripts\Activate.ps1`에 `$env:PYTHONUTF8="1"` 한 줄 추가.

---

## 직전 세션이 한 일 (오늘, round 2)

### 1. Docker Desktop 4.65.0 → 4.73.1 재설치
- 4.65.0의 `com.docker.service` 시작 실패 (2026-03-24 이후 사망) → 풀 재설치
- 설치 후 (a) `docker-desktop://` URI handler OpenWith 팝업 + (b) "Starting Docker Engine" 무한 반복 발생
- 원인: **`UseContainerdSnapshotter: true` + `EnableDockerAI: true`**가 4.73의 daemon 부팅을 막음
- 해결: `%APPDATA%\Docker\settings-store.json`에서 두 값 모두 `false`로 변경 → 10초 만에 daemon ready

### 2. Dev DB Dockerfile 호환성 수정
- Alpine이 `postgresql18`을 디폴트로 변경 → `apk add postgresql-pg_cron`이 PG18용 .so를 설치 → TimescaleDB 베이스(PG17)와 경로/ABI 불일치
- `20251030-rpi-pgcron/Dockerfile.rpi-pgcron`을 `pg_config --pkglibdir/--sharedir`로 경로 동적 탐지하도록 패치
- pg_cron 1.6.7가 **PG18 ABI**로 빌드된 바이너리라 PG17에서 `pqsignal_be` 심볼 못 찾음
- 최종 해결: `docker-compose.dev.yml`의 `command:` 오버라이드로 **pg_cron 일시 비활성** (dev 환경은 cron 불필요)

### 3. ecoanp DB 복원 (TimescaleDB 공식 절차)
- 첫 시도 (parallel pg_restore) → hypertable `TRUNCATE ONLY` 호환성 에러로 0 rows
- 올바른 절차:
  1. `DROP DATABASE ecoanp; CREATE DATABASE ecoanp TEMPLATE template0;`
  2. `CREATE EXTENSION timescaledb WITH VERSION '2.21.3';` (dump이 2.21.3 베이스)
  3. `SELECT timescaledb_pre_restore();`
  4. `pg_restore --no-owner --no-privileges` (single-thread)
  5. `SELECT timescaledb_post_restore();`
- 결과:
  - `alarm_history`: **750,727 rows**
  - `influx_hist`: **294,202 rows** (6 chunks, 시계열 메인)
  - `prediction_performance`: **4,764 rows** (8 chunks)
  - 6 hypertables 복원 (continuous_agg 5개는 2.21.3 → 2.27 catalog 차이로 누락 — 운영 영향 미미)

### 4. Reflex 한글 경로 인코딩 이슈 해결
- `UnicodeDecodeError: 'cp949' codec can't decode byte 0xeb` — `.gitignore` 읽을 때 Python이 cp949 디코딩 시도
- 해결: `$env:PYTHONUTF8 = "1"` + `$env:PYTHONIOENCODING = "utf-8"`
- 첫 부팅 230개 npm packages 설치 포함 ~90초

### 5. 최종 검증
- Frontend `http://localhost:14000` → HTTP 200, 23KB HTML ✓
- Backend `http://localhost:14001/ping` → "pong" ✓
- DB `edgeex-dev-db` healthy ✓

---

## ⚠️ 다음 세션을 위한 함정

### Docker Desktop 재시작 시
- **`UseContainerdSnapshotter`가 GUI 토글로 재활성화될 수 있음**. Settings → General에서 "Use containerd for pulling and storing images" 꺼져 있는지 확인.

### DB 컨테이너 재빌드 시
- `docker-compose.dev.yml`의 `command:` 오버라이드 유지 (pg_cron 비활성). cron 필요해지면 pg_cron source 빌드 추가 필요.
- `Dockerfile.rpi-pgcron`은 직전 세션이 수정. RPI 운영 영향 가능성 낮으나, RPI에서 재빌드 시 동작 확인 필요.

### ecoanp DB 재복원 시
- 반드시 `template0`로 `CREATE DATABASE` (template1 timescaledb 상속 회피)
- `CREATE EXTENSION timescaledb WITH VERSION '2.21.3';` — dump 버전과 맞춰야 함
- `pre_restore` → `pg_restore` → `post_restore` 순서 엄수

### Reflex 한글 경로
- Synology 원경로 그대로 사용 가능, 단 **`PYTHONUTF8=1` 필수**.
- Junction `C:\sync` → 원경로도 OK. 일관되게 하나만 쓸 것.

---

## 🐛 알려진 잔여 이슈

| 이슈 | 영향 | 대응 |
|---|---|---|
| pg_cron 비활성 | dev에서 schedule 작업 안 돌아감 | 운영(RPI)은 정상 |
| continuous_agg 5개 누락 | 일부 집계 뷰 없음 | 필요 시 수동 재생성 또는 dump 재생성 |
| TimescaleDB 2.21.3 ↔ 2.27 catalog 차이 | 일부 카탈로그 행 import 실패 | 데이터 쿼리 자체는 OK |

---

## 🔐 보안 미해결 (전 세션 인계 그대로)

- **Cloudflare Tunnel 토큰이 `docker-compose.yml`에 평문 노출** (line 112). 회수 필요.
- `01_remote_edgeex/` 진단 스크립트들에 SSH 패스워드 `!eonware` 하드코딩. 키 인증으로 전환 권장.

---

## 🗂 리팩토링 백로그 (유효)

| 우선순위 | 항목 | 비고 |
|---|---|---|
| H | `alarm_vectors` 6.5GB 테이블 조사 | 비정상 비대 |
| H | `forecast-scheduler` TimeoutError | 간헐 발생, 미해결 |
| M | 코드 중복 정리 | `alarms_*` 7버전, `forecast_player_*` 2버전, `trend_*_enhanced` 등 |
| M | DELTA_PRESSURE 12,412.5 bar 오류값 | Node-RED 변환 로직 |
| M | Docker image 4.49GB 경량화 | |
| M | Dangling images 7.47GB 정리 | `docker image prune` |
| L | InfluxDB measurement 변경 추적 체계 | eonware ↔ Node-RED 동기화 |

리팩토링 시작 시 `/pdca plan edgeex-refactoring` 권장.

---

## 📁 파일/경로 빠른 참조

| 항목 | 경로 |
|---|---|
| 풍도 폴더 (작업본진) | `C:\sync\00_ServerPC\reflex\reflex-rpi\reflex-rpi-local-deployment-poongdo` (junction) |
| 풍도 폴더 (원경로) | `C:\Users\Ipeop\SynologyDrive_강민구대표\SynologyDrive\00_ServerPC\reflex\reflex-rpi\reflex-rpi-local-deployment-poongdo` |
| venv | `C:\dev\venv-edgeex` (Python 3.12.10, reflex 0.8.16) |
| GitHub repo | https://github.com/grandbelly/reflex-edgeex-db (master) |
| 직전 commit (코드) | `2329856 feat: 풍도 사이트 신규 페이지/상태 + 인증 데이터 생성 스크립트` |
| Dev DB compose | `./docker-compose.dev.yml` (pg_cron 비활성 오버라이드) |
| Dev DB Dockerfile | `./20251030-rpi-pgcron/Dockerfile.rpi-pgcron` (PG paths 동적 탐지 수정) |
| 운영 compose (참고용) | `./docker-compose.yml` (RPI 운영, 토큰 노출 주의) |
| DB 백업 | `./backup/ecoanp_full_20251129_043928.dump` (389MB) |
| Reflex run log | `./reflex-run.log` |
| RPI SSH | `ssh tion@192.168.0.80` |
| RPI 앱 경로 | `/home/tion/deployment/20251030-rpi-finished/` |

---

## 🎯 사용자 의도 (변경 없음)

- 풍도 인스턴스 로컬에서 개발 + 디버그 → ✅ **환경 가동 완료**
- AI/ML 기능은 나중에 (Reflex+DB 핵심만 먼저)
- DB는 RPI 운영본 백업 복원하여 실데이터로 작업
- 작업물은 `grandbelly/reflex-edgeex-db` GitHub에 지속 push
- 이후 큰 그림은 "오래된 코드 리팩토링" (코드 중복 정리, 안정화)

---

_이 핸드오프 파일은 2026-05-18 round 2 Claude 세션이 작성. 다음 세션은 위 "다음 실행 방법"만 따라하면 즉시 개발 시작 가능._

---

## 2026-05-20 verify-0 (stage-0): PASS
- 결과: 14 commits 누적분 풍도 Docker 환경 부팅 검증 통과 — 15/15 라우트 HTTP 200, 0 traceback
- 다음 권장: Stage 4 Deep DEEP-1 분석으로 자동 진입
- 산출물: `reports/verify_2026-05-20.html`, commit `6106566`

## 2026-05-20 deep (stage-4-1): PARTIAL
- 결과: training_state/state.py (1,077 LoC) 분석 완료 — 7 @rx.event + 5 @rx.var + 8 setter 분류. 분리 후 ~600 LoC (AC2 통과) 예상. HIGH 위험 메서드 2개 (start_training 337L, save_model 309L)
- 다음 권장: Q1-Q4 사용자 답변 후 Step 5-8 (helper 모듈 4개 신규 작성 + state.py 교체)
- 산출물: `reports/deep1_analysis_2026-05-20.html`, commit (next)
