# Session Handoff — 2026-05-18 (Round 2)

다음 Claude Code 세션에게 전달하는 작업 인계서. 이 폴더에서 새 세션 시작 시 가장 먼저 읽을 것.

---

## 한 줄 요약

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
docker exec ksys-dev-db pg_isready -U postgres

# 4. Reflex 실행 — PYTHONUTF8 환경변수 필수!
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:TS_DSN = "postgresql://postgres:postgres@localhost:5432/ecoanp?sslmode=disable"
$env:POSTGRES_CONNECTION_STRING = "postgresql://postgres:postgres@localhost:5432/ecoanp?sslmode=disable"
$env:APP_ENV = "development"
C:\dev\venv-ksys\Scripts\python.exe -m reflex run

# 5. 접속: http://localhost:14000 (frontend) / http://localhost:14001 (backend)
```

**Tip**: 매번 PYTHONUTF8 입력하기 귀찮으면 `C:\dev\venv-ksys\Scripts\Activate.ps1`에 `$env:PYTHONUTF8="1"` 한 줄 추가.

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
- DB `ksys-dev-db` healthy ✓

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
- `01_remote_ksys/` 진단 스크립트들에 SSH 패스워드 `!eonware` 하드코딩. 키 인증으로 전환 권장.

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

리팩토링 시작 시 `/pdca plan ksys-refactoring` 권장.

---

## 📁 파일/경로 빠른 참조

| 항목 | 경로 |
|---|---|
| 풍도 폴더 (작업본진) | `C:\sync\00_ServerPC\reflex\reflex-rpi\reflex-rpi-local-deployment-poongdo` (junction) |
| 풍도 폴더 (원경로) | `C:\Users\Ipeop\SynologyDrive_강민구대표\SynologyDrive\00_ServerPC\reflex\reflex-rpi\reflex-rpi-local-deployment-poongdo` |
| venv | `C:\dev\venv-ksys` (Python 3.12.10, reflex 0.8.16) |
| GitHub repo | https://github.com/grandbelly/reflex-ksys-db (master) |
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
- 작업물은 `grandbelly/reflex-ksys-db` GitHub에 지속 push
- 이후 큰 그림은 "오래된 코드 리팩토링" (코드 중복 정리, 안정화)

---

_이 핸드오프 파일은 2026-05-18 round 2 Claude 세션이 작성. 다음 세션은 위 "다음 실행 방법"만 따라하면 즉시 개발 시작 가능._
