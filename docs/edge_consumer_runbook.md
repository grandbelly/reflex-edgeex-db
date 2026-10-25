# CR-EXAT-277 상위 Consumer 엣지 PC(`DESKTOP-HVKP484`) 통합 시험 실행 설명서 (Runbook)

본 문서는 오너 지시 `D-1025-05` 및 `edgeEX` PL 가이드(`20261025T095232+0900__cr277-upper-edge-integration-guide`) §2-H에 따라, 엣지 PC(`192.168.219.54`, `DESKTOP-HVKP484`)의 전담 세션(`edgeEX` Codex `term_fc879d47`)이 그대로 복사·실행할 수 있도록 작성된 절차서입니다.

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

git clone --branch cr277-edge-consumer https://github.com/grandbelly/reflex-ksys-db.git upper-consumer
Set-Location "$WorkRoot\upper-consumer"

# 회신 문서(prompts/edgeex_reply_from_upper_v1_4.md)에 명시된 고정 SHA 체크아웃
git checkout <COMMIT_SHA>
git rev-parse HEAD
```

---

## 2. Python 가상환경(venv) 생성 및 최소 의존성 설치

`requirements-edge-consumer.txt`에는 `aiokafka==0.14.0`, `asyncpg==0.31.0`, `psycopg[binary]==3.3.4` 3개만 고정되어 있습니다(`reflex` 등 불필요 패키지 미포함).

```powershell
Set-Location "C:\edgeex-it\cr277\upper-consumer"

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# (A) 온라인 설치 시:
.\.venv\Scripts\pip.exe install -r requirements-edge-consumer.txt

# (B) 오프라인 바퀴 파일(wheels 폴더)로 설치 시:
# .\.venv\Scripts\pip.exe install --no-index --find-links .\wheels -r requirements-edge-consumer.txt

# 설치된 판 확인
.\.venv\Scripts\pip.exe list
```

---

## 3. 상위 시험 DB(`edgeex-it-upperdb`, `127.0.0.1:55432`) 스키마 적용

`migrations/edge_test_schema.sql`을 **2회 연속 실행**(멱등성 확인)한 뒤, 이어서 `migrations/014_create_edgeex_vqt_lossless.sql`을 **1회 실행**합니다.

```powershell
Set-Location "C:\edgeex-it\cr277\upper-consumer"

# 1차 실행 (표 5종 및 하이퍼테이블/고유 제약 생성)
Get-Content -Raw .\migrations\edge_test_schema.sql | docker exec -i edgeex-it-upperdb psql -v ON_ERROR_STOP=1 -U postgres -d postgres

# 2차 실행 (IF NOT EXISTS 멱등 재실행 — 오류 0건 확인)
Get-Content -Raw .\migrations\edge_test_schema.sql | docker exec -i edgeex-it-upperdb psql -v ON_ERROR_STOP=1 -U postgres -d postgres

# 이어서 migration 014 실행 (오류 0건 확인)
Get-Content -Raw .\migrations\014_create_edgeex_vqt_lossless.sql | docker exec -i edgeex-it-upperdb psql -v ON_ERROR_STOP=1 -U postgres -d postgres

# 생성된 표 5개 확인 (influx_tag, viewer_tag, influx_hist, alarm_history, edgeex_vqt_raw)
docker exec -i edgeex-it-upperdb psql -U postgres -d postgres -c "\dt public.*"
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
KAFKA_CONSUMER_GROUP=ksys-upper-it-cr277
KAFKA_ENABLED=true
KAFKA_TOPICS=edgeex.test.telemetry.vqt,edgeex.test.alarms.events,edgeex.test.health.status
"@ | Set-Content -Encoding UTF8 .\.env
```

---

## 5. 상위 Consumer 백그라운드 기동 및 로그 파일 위치

```powershell
Set-Location "C:\edgeex-it\cr277\upper-consumer"
New-Item -ItemType Directory -Force -Path .\logs | Out-Null

$ConsumerProc = Start-Process -FilePath ".\.venv\Scripts\python.exe" `
    -ArgumentList "-u", "-m", "ksys_app.integration.kafka_consumer" `
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

기동 후 3~5초 뒤 아래 명령으로 **Consumer Group(`ksys-upper-it-cr277`) 가입** 및 **시험 토픽 3종 파티션(`3 / 1 / 1`) 할당**을 확인합니다.

```powershell
# 1) 로그에서 그룹 가입 및 파티션 3/1/1 할당 확인
Select-String -Path "C:\edgeex-it\cr277\upper-consumer\logs\consumer_stdout.log" `
    -Pattern "Connected to|Group joined & partitions assigned"

# 기대 출력 예시:
# [KafkaConsumer] Connected to 127.0.0.1:9092 (group=ksys-upper-it-cr277, enable_auto_commit=False, topics=('edgeex.test.telemetry.vqt', 'edgeex.test.alarms.events', 'edgeex.test.health.status'))
# [KafkaConsumer] Group joined & partitions assigned (group=ksys-upper-it-cr277): counts={'edgeex.test.alarms.events': 1, 'edgeex.test.health.status': 1, 'edgeex.test.telemetry.vqt': 3} detail={'edgeex.test.telemetry.vqt': [0, 1, 2], 'edgeex.test.alarms.events': [0], 'edgeex.test.health.status': [0]}

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

### 8.1 상위 시험 DB 대조 질의 실행
`query_edgeex_vqt_parity.py`는 `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY` 및 `SET statement_timeout = 10000`으로 동작하며, 지정된 시간 구간 `[start_ms, end_ms]`를 **1분(`60,000 ms`) 조각으로 나누어** 조각별 건수·`xor17`·`xor53`을 구한 뒤 파이썬에서 합산(`SUM` 및 `^` XOR)합니다.

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
