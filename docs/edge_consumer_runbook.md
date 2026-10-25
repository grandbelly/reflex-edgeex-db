# CR-EXAT-277 상위 Consumer 및 상위 웹 앱(`edgeex_app`) 엣지 PC(`DESKTOP-HVKP484`) 통합 시험 실행 설명서 (Runbook)

본 문서는 오너 지시 `D-1025-05` 및 `edgeEX` PL 가이드(`20261025T095232+0900__cr277-upper-edge-integration-guide`) §2-H, 그리고 `v1.6` 웹 앱 브라우저 통합 시험 지시에 따라, 엣지 PC(`192.168.219.54`, `DESKTOP-HVKP484`)의 전담 세션(`edgeEX` Codex `term_fc879d47`)이 그대로 복사·실행할 수 있도록 작성된 절차서입니다.

---

## 0. 사전 전제 (`127.0.0.1` 루프백 단일 호스트 격리 시험)

- **작업 루트 폴더**: `C:\edgeex-it\cr277\` (운전 설치 `C:\ProgramData\DohwaEdge`와 완전 분리)
- **시험 브로커 컨테이너 (`edgeex-it-kafka`)**: `127.0.0.1:9092` (`PLAINTEXT`)
  - 토픽 3종:
    - `edgeex.test.telemetry.vqt` (파티션 `3`, 복제 `1`, `retention.ms=86400000`)
    - `edgeex.test.alarms.events` (파티션 `1`, 복제 `1`, `retention.ms=86400000`)
    - `edgeex.test.health.status` (파티션 `1`, 복제 `1`, `retention.ms=86400000`)
- **상위 시험 DB 컨테이너 (`edgeex-it-upperdb`)**: `127.0.0.1:55432` (`timescale/timescaledb:2.28.2-pg16`)

---

## 1. 저장소 복제(Clone) 및 고정 SHA 체크아웃

```powershell
$WorkRoot = "C:\edgeex-it\cr277"
New-Item -ItemType Directory -Force -Path $WorkRoot | Out-Null
Set-Location $WorkRoot

git clone https://github.com/grandbelly/reflex-edgeex-db.git upper-consumer
Set-Location "$WorkRoot\upper-consumer"

# 회신 문서(prompts/edgeex_reply_from_upper_v1_6.md)에 명시된 고정 SHA 체크아웃
git fetch origin
git checkout <COMMIT_SHA>
git rev-parse HEAD
```

---

## 2. Python 가상환경(venv) 생성 및 의존성 설치

- **Consumer 단독 구동 시**: `requirements-edge-consumer.txt` (`aiokafka==0.14.0`, `asyncpg==0.31.0`, `psycopg[binary]==3.3.4` 3개)
- **상위 웹 앱(`edgeex_app`) + Consumer 함께 구동 시**: `requirements-edge-web.txt` (`reflex==0.8.16` 포함 22개 고정판)

```powershell
Set-Location "C:\edgeex-it\cr277\upper-consumer"

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# (A) Consumer + 상위 웹 앱(Reflex) 통합 설치 시:
.\.venv\Scripts\pip.exe install -r requirements-edge-web.txt

# (B) Consumer만 단독 설치 시:
# .\.venv\Scripts\pip.exe install -r requirements-edge-consumer.txt

# 설치된 판 확인
.\.venv\Scripts\pip.exe list
```

---

## 3. 상위 시험 DB(`edgeex-it-upperdb`, `127.0.0.1:55432`) 스키마 적용

`migrations/edge_test_schema.sql`을 **2회 연속 실행**(멱등성 확인)한 뒤, 이어서 `migrations/014_create_edgeex_vqt_lossless.sql`을 **1회 실행**합니다.

```powershell
Set-Location "C:\edgeex-it\cr277\upper-consumer"

# 1차 실행 (표 7종, 뷰 5종 및 하이퍼테이블/고유 제약 생성)
Get-Content -Raw .\migrations\edge_test_schema.sql | docker exec -i edgeex-it-upperdb psql -v ON_ERROR_STOP=1 -U postgres -d postgres

# 2차 실행 (IF NOT EXISTS / CREATE OR REPLACE VIEW 멱등 재실행 — 오류 0건 확인)
Get-Content -Raw .\migrations\edge_test_schema.sql | docker exec -i edgeex-it-upperdb psql -v ON_ERROR_STOP=1 -U postgres -d postgres

# 이어서 migration 014 실행 (오류 0건 확인)
Get-Content -Raw .\migrations\014_create_edgeex_vqt_lossless.sql | docker exec -i edgeex-it-upperdb psql -v ON_ERROR_STOP=1 -U postgres -d postgres

# 생성된 표 및 뷰 확인
docker exec -i edgeex-it-upperdb psql -U postgres -d postgres -c "\dt public.*"
docker exec -i edgeex-it-upperdb psql -U postgres -d postgres -c "\dv public.*"
```

---

## 4. 시험 전용 `.env` 생성

`.env.edge-test.example`을 복사하여 `.env`를 만들고, 엣지에서만 쓰는 시험 DB 접속 문자열(`TS_DSN`)을 채웁니다.

```powershell
Set-Location "C:\edgeex-it\cr277\upper-consumer"
Copy-Item .\.env.edge-test.example .\.env -Force

# 예시: 엣지에서 생성한 시험 DB 암호($DbPass)를 넣어 .env 작성
$DbPass = "<EDGE_LOCAL_TEST_DB_PASSWORD>"
@"
TS_DSN=postgresql://postgres:$DbPass@127.0.0.1:55432/postgres?sslmode=disable
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
KAFKA_CONSUMER_GROUP=edgeex-upper-it-cr277
KAFKA_ENABLED=true
KAFKA_TOPICS=edgeex.test.telemetry.vqt,edgeex.test.alarms.events,edgeex.test.health.status
ENABLE_AI_FEATURES=false
APP_VERSION=PART
KAFKA_IN_APP_CONSUMER=false
"@ | Set-Content -Encoding UTF8 .\.env
```

---

## 5. 상위 Consumer 백그라운드 기동 및 로그 파일 위치

```powershell
Set-Location "C:\edgeex-it\cr277\upper-consumer"
New-Item -ItemType Directory -Force -Path .\logs | Out-Null

$ConsumerProc = Start-Process -FilePath ".\.venv\Scripts\python.exe" `
    -ArgumentList "-u", "-m", "edgeex_app.integration.kafka_consumer" `
    -WorkingDirectory "C:\edgeex-it\cr277\upper-consumer" `
    -RedirectStandardOutput "C:\edgeex-it\cr277\upper-consumer\logs\consumer_stdout.log" `
    -RedirectStandardError  "C:\edgeex-it\cr277\upper-consumer\logs\consumer_stderr.log" `
    -NoNewWindow -PassThru

$ConsumerProc.Id | Set-Content "C:\edgeex-it\cr277\upper-consumer\logs\consumer.pid"
Write-Host "Consumer started with PID=$($ConsumerProc.Id)"
```

### 로그 및 상태 파일 위치
1. **표준 출력 로그**: `C:\edgeex-it\cr277\upper-consumer\logs\consumer_stdout.log`
2. **표준 에러 로그**: `C:\edgeex-it\cr277\upper-consumer\logs\consumer_stderr.log`
3. **실시간 메트릭/파티션 JSON**: `C:\edgeex-it\cr277\upper-consumer\logs\consumer_metrics.json`
4. **세션 상세 로그**: `C:\edgeex-it\cr277\upper-consumer\logs\session_*\app.log`

---

## 6. 정상 기동 판단 기준 (그룹 가입 및 파티션 `3 / 1 / 1` 할당 확인)

기동 후 3~5초 뒤 아래 명령으로 **Consumer Group(`edgeex-upper-it-cr277`) 가입** 및 **시험 토픽 3종 파티션(`3 / 1 / 1`) 할당**을 확인합니다.

```powershell
# 1) 로그에서 그룹 가입 및 파티션 3/1/1 할당 확인
Select-String -Path "C:\edgeex-it\cr277\upper-consumer\logs\consumer_stdout.log" `
    -Pattern "Connected to|Group joined & partitions assigned"

# 기대 출력 예시:
# [KafkaConsumer] Connected to 127.0.0.1:9092 (group=edgeex-upper-it-cr277, enable_auto_commit=False, topics=('edgeex.test.telemetry.vqt', 'edgeex.test.alarms.events', 'edgeex.test.health.status'))
# [KafkaConsumer] Group joined & partitions assigned (group=edgeex-upper-it-cr277): counts={'edgeex.test.alarms.events': 1, 'edgeex.test.health.status': 1, 'edgeex.test.telemetry.vqt': 3} detail={'edgeex.test.telemetry.vqt': [0, 1, 2], 'edgeex.test.alarms.events': [0], 'edgeex.test.health.status': [0]}

# 2) 실시간 상태 JSON 파일로 확인
Get-Content "C:\edgeex-it\cr277\upper-consumer\logs\consumer_metrics.json"
```

정상 판단 기준:
- `metrics.broker_status` == `"CONNECTED"`
- `metrics.enable_auto_commit` == `false`
- `metrics.subscribed_topics` == `["edgeex.test.telemetry.vqt", "edgeex.test.alarms.events", "edgeex.test.health.status"]` (운영 토픽 미포함)
- `metrics.assigned_partitions`:
  - `edgeex.test.telemetry.vqt`: `[0, 1, 2]` (3개)
  - `edgeex.test.alarms.events`: `[0]` (1개)
  - `edgeex.test.health.status`: `[0]` (1개)

---

## 7. `duplicates_absorbed` 및 배치 커밋 확인

시나리오 6(브로커 순단 및 TSDB 역주입 재전송) 등 시험 중 중복 흡수 건수(`duplicates_absorbed`)와 무손실 적재 건수(`vqt_raw_rows_written`, `bad_quality_preserved`)는 아래 두 가지 방법으로 즉시 확인합니다.

```powershell
# 방법 1: consumer_metrics.json 조회
$m = (Get-Content "C:\edgeex-it\cr277\upper-consumer\logs\consumer_metrics.json" | ConvertFrom-Json).metrics
$m | Select-Object commits_succeeded, telemetry_count, vqt_raw_rows_written, bad_quality_preserved, duplicates_absorbed, alarm_count, health_count, db_errors

# 방법 2: consumer_stdout.log 배치 커밋 로그 조회
Select-String -Path "C:\edgeex-it\cr277\upper-consumer\logs\consumer_stdout.log" -Pattern "Batch committed|Stopped" | Select-Object -Last 10
```

---

## 8. 읽기 전용 대조 질의 (`scripts/query_edgeex_vqt_parity.py`) 및 행 서명 규칙

### 8.1 상위 시험 DB 대조 질의 실행 (`win32` `WindowsSelectorEventLoopPolicy` 적용 완료)
`query_edgeex_vqt_parity.py`는 Windows(`sys.platform == "win32"`)에서 실행 시 자동으로 `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`를 설정하여 `psycopg.AsyncConnection`과 `ProactorEventLoop` 간 충돌 없이 즉시 동작합니다. 또한 `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY` 및 `SET statement_timeout = 10000`으로 동작하며, 지정된 시간 구간 `[start_ms, end_ms]`를 **1분(`60,000 ms`) 조각으로 나누어** 조각별 건수·`xor17`·`xor53`을 구한 뒤 파이썬에서 합산(`SUM` 및 `^` XOR)합니다.

```powershell
Set-Location "C:\edgeex-it\cr277\upper-consumer"

.\.venv\Scripts\python.exe .\scripts\query_edgeex_vqt_parity.py `
    --site-id "<SITE_ID>" `
    --start-ms <START_EPOCH_MS> `
    --end-ms <END_EPOCH_MS> `
    --out "C:\edgeex-it\cr277\upper_vqt_parity_result.json"
```
- `--duplicates-absorbed` 인자를 생략하면 `logs\consumer_metrics.json`의 `metrics.duplicates_absorbed` 값을 자동으로 읽어 결과 JSON에 포함합니다.

### 8.2 행 서명 문자열(`row_sig`) 바이트 규격 (§2-G 고정 계약)

양쪽(엣지 TSDB vs 상위 `public.edgeex_vqt_raw`) 대조 질의가 0 차이를 산출하기 위한 **고정 행 서명(`row_sig`) 규칙**입니다:

```text
site_id|tag_id|ts_ms|final_val_str|final_quality|integ_class|reasons_csv
```

| 순서 | 필드명 | 생성 규칙 (PostgreSQL) | 예시 |
| :---: | :--- | :--- | :--- |
| 1 | `site_id` | `site_id::TEXT` | `edge-acceptance` |
| 2 | `tag_id` | `tag_id::TEXT` | `TAG_001` |
| 3 | `ts_ms` | `trunc(EXTRACT(EPOCH FROM ts) * 1000)::BIGINT::TEXT` (`int(ts.timestamp()*1000)` 내림 규칙과 동일) | `1729785600000` |
| 4 | `final_val_str` | `CASE WHEN final_val IS NULL THEN 'NULL' ELSE to_char(final_val, 'FM999999999990.000000000') END` (소수점 이하 고정 9자리) | `12.340000000` 또는 `NULL` |
| 5 | `final_quality` | `final_quality::TEXT` (`0`, `1`, `2`) | `2` |
| 6 | `integ_class` | `integ_class::TEXT` (`0`..`5`) | `0` |
| 7 | `reasons_csv` | 비트 0..17(`core/conditioning.py` `REASON_LABELS`) 순서의 사유 이름을 공백 없이 `,`로 이은 문자열. 사유가 없으면 빈 문자열 `''` | `SOURCE_BAD,LOCF_HELD` 또는 `''` |

- **구분자 결합**: `concat_ws('|', site_id, tag_id, ts_ms::TEXT, final_val_str, final_quality::TEXT, integ_class::TEXT, reasons_csv)`
  - 주의: `reasons_csv`가 빈 문자열(`''`)일 때도 `NULL`이 아닌 `''`을 넘기므로 마지막 `|`가 항상 유지됩니다(예: `edge-acceptance|TAG_001|1729785600000|12.340000000|2|0|`).
- **64비트 해시 및 XOR**:
  - `xor17`: `COALESCE(bit_xor(hashtextextended(row_sig, 17)), 0)::BIGINT`
  - `xor53`: `COALESCE(bit_xor(hashtextextended(row_sig, 53)), 0)::BIGINT`

#### 엣지 TSDB(`tag_raw` + `tag_cond`) 측 동일 서명 생성 참조 SQL 조각
엣지 TSDB에서 `r.reason_mask` 정수 비트열을 동일한 `reasons_csv`로 변환할 때는 아래 배열/비트 매핑(비트 0..17)을 사용하면 바이트 단위까지 100% 동일합니다:
```sql
COALESCE(
    (
        SELECT string_agg(lbl, ',' ORDER BY bit)
        FROM unnest(ARRAY[
            'SOURCE_BAD', 'RANGE_INVALID', 'MEDIAN_APPLIED', 'EWMA_APPLIED',
            'OUTLIER_REPLACED', 'LOCF_HELD', 'INTERP_BACKFILLED', 'STALE_EXPIRED',
            'WARMUP', 'STATE_RESET', 'LATE_ARRIVAL', 'TIME_INVALID',
            'RANGE_UNRESOLVED', 'NON_NUMERIC', 'COND_ERROR', 'FLATLINE',
            'HUNTING', 'COLLECTION_STOPPED'
        ]) WITH ORDINALITY AS t(lbl, ord)
        CROSS JOIN LATERAL (SELECT (ord - 1)::INT AS bit) b
        WHERE (r.reason_mask & (1 << b.bit)) <> 0
    ),
    ''
) AS reasons_csv
```

### 8.3 판별 민감도 확인 (§3 5단계 — 시나리오 전 복사 표 1행 변조 시 XOR 변화 확인)
```sql
-- 상위 시험 DB 내 임시 복사 표에서 1행 변조 시 xor17/xor53 변화 확인 예시
CREATE TEMP TABLE tmp_vqt_check AS SELECT * FROM public.edgeex_vqt_raw LIMIT 100;
-- 변조 전 해시와 1행의 final_val 또는 reasons 변조 후 해시가 즉시 달라지는지 확인
```

---

## 9. 상위 Consumer 정지 및 정리 (§3 8단계)

```powershell
# 1) Consumer 프로세스 정지
$PidFile = "C:\edgeex-it\cr277\upper-consumer\logs\consumer.pid"
if (Test-Path $PidFile) {
    $TargetPid = [int](Get-Content $PidFile)
    Stop-Process -Id $TargetPid -Force -ErrorAction SilentlyContinue
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped Consumer PID=$TargetPid"
}

# 2) 최종 메트릭 확인
Get-Content "C:\edgeex-it\cr277\upper-consumer\logs\consumer_metrics.json"
```

---

## 10. 엣지에서 상위 웹 앱(`edgeex_app`) 실행 및 브라우저 검증 (v1.6)

### 10.1 필요한 패키지 (`requirements-edge-web.txt` 고정판)
AI/ML 예측 모델(`torch`, `sentence-transformers`, `statsforecast`, `xgboost`, `prophet`)은 `ENABLE_AI_FEATURES=false` (`APP_VERSION=PART`) 설정 시 로드하지 않도록 분리되어 있으므로, 아래 **22개 고정 패키지**가 담긴 `requirements-edge-web.txt`만 설치하면 상위 웹 앱과 Consumer, 대조 스크립트가 모두 동작합니다.

| 패키지 | 고정 버전 | 용도 |
| :--- | :--- | :--- |
| `reflex` | `0.8.16` | 상위 웹 앱 프레임워크 (프런트엔드/백엔드 서버) |
| `reflex-chakra` | `0.8.2.post1` | Reflex UI 컴포넌트 |
| `aiokafka` | `0.14.0` | 비동기 Kafka Consumer |
| `asyncpg` | `0.31.0` | 웹 앱 및 Consumer 비동기 PostgreSQL/TimescaleDB 풀 |
| `psycopg` / `psycopg-binary` / `psycopg-pool` | `3.3.4` / `3.3.4` / `3.3.1` | 대조 질의 및 DB 유틸리티 |
| `SQLAlchemy` / `sqlmodel` | `2.0.50` / `0.0.38` | ORM 및 비동기 세션 |
| `plotly` | `6.7.0` | `/edge-monitor` 및 `/trend` 차트 렌더링 |
| `pandas` / `numpy` / `scipy` | `3.0.3` / `2.4.6` / `1.15.3` | 시계열 데이터 처리 |
| `pydantic` / `cachetools` | `2.13.4` / `7.1.4` | 상태 모델 및 캐시 |
| `pytz` / `tzdata` | `2025.2` / `2026.2` | 타임존 처리 |
| `cryptography` / `watchdog` / `dill` / `httpx` / `aiohttp` | `48.0.0` / `6.0.0` / `0.4.1` / `0.28.1` / `3.13.5` | 런타임 유틸리티 |

### 10.2 Node.js 필요 여부
- **필요함**: Reflex(`0.8.16`)는 React(Next.js) 프런트엔드를 구동하기 위해 **Node.js (`>= 18.18.0`, 권장 20.x/22.x LTS)** 를 사용합니다.
- 엣지 PC의 `PATH`에 `node`가 설치되어 있으면 Reflex가 이를 그대로 사용하며, 설치되어 있지 않고 인터넷 연결이 가능하면 첫 `reflex init` 실행 시 `%LOCALAPPDATA%\reflex` 내부에 자동으로 Node.js/Bun 런타임을 내려받습니다.

### 10.3 화면 구동에 필요한 추가 DB 표·뷰 (빈 DB에 멱등)
`migrations/edge_test_schema.sql`에 이미 **웹 화면 구동에 필요한 추가 표 2개와 뷰 5개가 모두 포함**되어 있습니다(모두 `CREATE TABLE IF NOT EXISTS` 및 `CREATE OR REPLACE VIEW`로 작성되어 빈 DB에 2회 이상 실행해도 멱등):
1. **추가 표 2개**:
   - `public.edgeex_health_latest` (`PRIMARY KEY (site_id)`): Consumer가 `health` 토픽 수신 시 사이트별 최신 상태를 UPSERT하며, `/edge-monitor` 화면의 `/health` 상태 카드가 직접 조회합니다.
   - `public.influx_qc_rule` (`PRIMARY KEY (tag_name)`): 대시보드(`/`) 및 알람(`/alarms`) 화면의 QC 임계값 조인용 표입니다.
2. **추가 뷰 5개**:
   - `public.influx_latest`, `public.influx_latest_status`, `public.influx_latest_1m`, `public.influx_latest_5m`, `public.influx_latest_1h`: 대시보드(`/`), 트렌드(`/trend`), 워크플로우(`/workflow`), 통신 상태(`/comm`) 화면이 참조하는 최신값 뷰입니다.

### 10.4 로그인 필요 여부 및 시험 계정
- **로그인 불필요 (인증 없음)**: `edgeex_app`은 별도의 웹 로그인/세션 인증 절차가 없습니다.
- 브라우저(`agent-browser`)로 `http://127.0.0.1:3100/edge-monitor` 또는 `http://127.0.0.1:3100/`에 접속하면 **계정 생성이나 로그인 입력 없이 즉시 대시보드 화면이 열립니다**.
- DB 접속 암호는 엣지에서 생성한 `edgeex-it-upperdb`(`127.0.0.1:55432`)의 PostgreSQL 암호를 `.env`의 `TS_DSN`에 기입하면 됩니다.

### 10.5 상위 웹 앱 기동 명령 (`127.0.0.1` 전용 바인드: 프런트 `3100` / 백엔드 `8100`)

> **중요**: 5절에서 상위 Consumer(`python -m edgeex_app.integration.kafka_consumer`)를 이미 별도 프로세스로 띄웠으므로, 웹 앱 프로세스에서는 `KAFKA_IN_APP_CONSUMER=false`를 유지하여 Consumer 그룹 리밸런싱 충돌을 방지합니다. `/edge-monitor` 페이지는 3초마다 `edgeex-it-upperdb`(`127.0.0.1:55432`)의 `edgeex_vqt_raw`, `alarm_history`, `edgeex_health_latest` 표와 `logs/consumer_metrics.json`을 직접 읽어 화면을 갱신합니다.

```powershell
Set-Location "C:\edgeex-it\cr277\upper-consumer"
New-Item -ItemType Directory -Force -Path .\logs | Out-Null

# 1) 환경변수 설정 (127.0.0.1 루프백 전용 바인드 및 경량 모드)
$env:HOSTNAME = "127.0.0.1"
$env:ENABLE_AI_FEATURES = "false"
$env:APP_VERSION = "PART"
$env:KAFKA_IN_APP_CONSUMER = "false"

# 2) 최초 1회 Reflex 프런트엔드 초기화 (.web 디렉터리 생성)
.\.venv\Scripts\reflex.exe init

# 3) 상위 웹 앱 백그라운드 기동 (프런트엔드 127.0.0.1:3100 / 백엔드 127.0.0.1:8100)
$WebProc = Start-Process -FilePath ".\.venv\Scripts\reflex.exe" `
    -ArgumentList "run", "--env", "dev", "--backend-host", "127.0.0.1", "--frontend-port", "3100", "--backend-port", "8100", "--loglevel", "info" `
    -WorkingDirectory "C:\edgeex-it\cr277\upper-consumer" `
    -RedirectStandardOutput "C:\edgeex-it\cr277\upper-consumer\logs\web_stdout.log" `
    -RedirectStandardError  "C:\edgeex-it\cr277\upper-consumer\logs\web_stderr.log" `
    -NoNewWindow -PassThru

$WebProc.Id | Set-Content "C:\edgeex-it\cr277\upper-consumer\logs\web.pid"
Write-Host "Upper Web App started with PID=$($WebProc.Id)"
```

#### 포트 리스닝 및 접속 확인
```powershell
# 3100(프런트엔드) 및 8100(백엔드) 포트가 127.0.0.1에서 열렸는지 확인
Test-NetConnection -ComputerName 127.0.0.1 -Port 3100
Test-NetConnection -ComputerName 127.0.0.1 -Port 8100

# 브라우저 접속 주소:
# - Edge 관제 페이지: http://127.0.0.1:3100/edge-monitor
# - 미니 SCADA 대시보드: http://127.0.0.1:3100/
# - 알람 이력 페이지: http://127.0.0.1:3100/alarms
```

#### 상위 웹 앱 정지 명령
```powershell
$WebPidFile = "C:\edgeex-it\cr277\upper-consumer\logs\web.pid"
if (Test-Path $WebPidFile) {
    $TargetPid = [int](Get-Content $WebPidFile)
    Stop-Process -Id $TargetPid -Force -ErrorAction SilentlyContinue
    Remove-Item $WebPidFile -Force -ErrorAction SilentlyContinue
}
```

---

### 10.6 브라우저 시험 기대 화면 (`/edge-monitor`) 및 연기 시험(Smoke Test) 데이터 기대값

브라우저(`agent-browser`)로 `http://127.0.0.1:3100/edge-monitor` 접속 시 화면은 **상단 KPI 카드 5개**와 **하단 데이터 섹션 5개**로 구성되며, 각 영역에 고정 `id` 및 `class`가 부여되어 있습니다.

#### A. `/edge-monitor` 화면 구성 요소 (DOM ID 매핑)
1. **상단 KPI 요약 타일 5개**:
   - `#kpi-edge-site`: **연결된 Edge 사이트** (사이트 수, Health 상태, 활성 `site_id`, 태그 종수)
   - `#kpi-vqt-total`: **적재된 VQT 표본 (`edgeex_vqt_raw`)** (전체 VQT 행 수, `BAD(품질0)` NULL 보존 건수, `GOOD` / `UNCERTAIN` / `중복흡수` 건수)
   - `#kpi-vqt-quality`: **VQT 유효 품질율 (`GOOD`)** (`GOOD` 비율 `%`, `BAD` 건수, `GOOD / 전체` 행 수)
   - `#kpi-edge-protection`: **전처리 이상치·결측 방어** (`Spike / LOCF` 건수, `STALE · HUNT · STOP` 건수)
   - `#kpi-alarm-health`: **경보 및 Health 수신** (`alarm_history` 경보 건수, `edgeex_health_latest` 수신 건수 및 상태)
2. **하단 상세 섹션 5개**:
   - `#section-health-status`: **엣지 `/health` 상태 스냅샷 (`edgeex_health_latest`)** (`.edge-health-item` 행에 `site_id`, `status`, `Liveness`, `ts_ms`, `summary` 표시)
   - `#section-tag-latest` (`#table-tag-latest` / `#tbody-tag-latest`): **태그별 최신 VQT 스냅샷 (`DISTINCT ON tag_id`)** (각 태그의 최신 시각, `RAW`, `COND`, `FINAL (최종값)`, `품질 (Quality)`, `INTEG 상태`, `사유 비트 (reasons)`)
   - `#section-vqt-all-rows` (`#table-vqt-history` / `#tbody-vqt-history`): **VQT 무손실 적재 이력 (`edgeex_vqt_raw` 전수 조회)** (최근 적재된 모든 VQT 표본 행을 시간 역순으로 표시)
   - `#section-edge-alarms` (`#table-edge-alarms` / `#tbody-edge-alarms`): **엣지 경보 수신 이력 (`alarm_history`)** (`event_id`, `태그 ID`, `등급 (Level)`, `경보 메시지`, `원인 · 상태`, `해제 여부`)
   - `#section-vqt-chart`: **태그 시계열 비교 차트 (`RAW vs COND vs FINAL`)** (Plotly 차트)

#### B. 연기 시험 데이터(**VQT 8행 [정상 7행 + BAD 1행], 경보 1건, Health 1건**) 투입 시 기대 표시값

연기 시험 데이터(총 VQT **8행** 중 `final_quality=2(GOOD)` **7행** + `final_quality=0(BAD, final_val=null)` **1행**, 경보 **1건**, Health **1건**)가 시험 토픽 3종을 통해 적재된 직후 `/edge-monitor`에서 보여야 할 정확한 값은 다음과 같습니다:

| 화면 영역 (DOM ID) | 항목 | 기대 표시값 |
| :--- | :--- | :--- |
| **`#kpi-edge-site`** | 연결된 Edge 사이트 | **`1`** 개소 · 배지: **`Health: OK`** (또는 수신된 `status` 값, 기본 `"OK"`) · 부제: `Site: <시험 site_id> · 태그 <고유 태그 수>종` |
| **`#kpi-vqt-total`** | 적재된 VQT 표본 (`edgeex_vqt_raw`) | **`8`** 행 · 배지: **`BAD(품질0): 1건 NULL 보존`** · 부제: **`GOOD 7 · UNCERTAIN 0 · 중복흡수 0`** (UNCERTAIN 표본이 N건이면 `GOOD (7-N) · UNCERTAIN N`) |
| **`#kpi-vqt-quality`** | VQT 유효 품질율 (`GOOD`) | **`87.5`** `%` (8행 중 GOOD 7행 기준: `7 / 8 * 100 = 87.5%`) · 배지: **`BAD 1건`** · 부제: **`GOOD 7 / 전체 8행`** |
| **`#kpi-edge-protection`** | 전처리 이상치·결측 방어 | `reasons` 비트에 포함된 방어 사유 합계 (예: BAD 1행이 `COLLECTION_STOPPED`이면 `STOP 1` 표시, `OUTLIER_REPLACED`/`LOCF_HELD`가 있으면 해당 건수 표시) |
| **`#kpi-alarm-health`** | 경보 및 Health 수신 | **`1`** 건 · 배지: **`Health 1건 (OK)`** · 부제: `alarm_history · edgeex_health_latest` |
| **`#section-health-status`** | 엣지 `/health` 상태 스냅샷 | 우측 상단 배지: **`수신 사이트: 1건`** · `.edge-health-item` 1행 표시: `.edge-health-site-id` = `<site_id>`, 상태 배지 = **`OK`** (또는 페이로드의 `status`), `.edge-health-ts-ms` = `ts_ms: <health ts_ms>` |
| **`#section-tag-latest`** (`#tbody-tag-latest`) | 태그별 최신 VQT 스냅샷 | 고유 `tag_id` 개수만큼의 행(`.edge-latest-row`) 표시. 최신 표본이 정상(`final_quality=2`)인 태그는 `FINAL (최종값)`에 소수점 3자리 수치와 초록색 **`GOOD (2)`** 배지 표시; 최신 표본이 불량(`final_quality=0`)인 태그는 `FINAL (최종값)`에 빨간 글씨 **`NULL (BAD 보존)`** 과 빨간색 **`BAD (0)`** 배지 표시 |
| **`#section-vqt-all-rows`** (`#tbody-vqt-history`) | VQT 무손실 적재 이력 (`edgeex_vqt_raw` 전수) | 우측 상단 배지: **`전체 적재: 8행 (BAD: 1행)`** · 표 본문(`#tbody-vqt-history`)에 **총 8개 행(`.edge-vqt-row`)** 모두 표시:<br>- **정상 7개 행**: `FINAL (최종값)`에 확정 수치 표시, `품질 (Quality)` 열에 초록색 **`GOOD (2)`** 배지 표시<br>- **불량(BAD) 1개 행**: 연한 적색 배경 강조, `FINAL (최종값)` 열(`.edge-vqt-final-val`)에 **`NULL (BAD 보존)`** 표시, `품질 (Quality)` 열(`.edge-vqt-quality`)에 빨간색 **`BAD (0)`** 배지 표시, `사유 비트 (reasons)` 열에 해당 사유 이름(예: `SOURCE_BAD` 또는 `COLLECTION_STOPPED`) 표시 |
| **`#section-edge-alarms`** (`#tbody-edge-alarms`) | 엣지 경보 수신 이력 (`alarm_history`) | 우측 상단 배지: **`경보 건수: 1건`** · 표 본문(`#tbody-edge-alarms`)에 **1개 행(`.edge-alarm-row`)** 표시:<br>- `.edge-alarm-event-id`: 경보 JSON의 `event_id`<br>- `.edge-alarm-tag-id`: 경보 JSON의 `tag_id` (태그 없는 시스템 경보면 **`__SYSTEM__`**)<br>- `.edge-alarm-level`: `CRITICAL` / `WARNING` / `INFO` 배지<br>- `.edge-alarm-message`: 경보 메시지(`message` 또는 `[state] alarm_type`)<br>- `해제 여부`: 미해제 시 빨간색 **`ACTIVE`** (해제 시 초록색 **`RESOLVED`**) |
