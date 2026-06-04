"""
Virtual Data Injection Script
- 100태그(기본) 등록 + 5분 간격 랜덤 센서 데이터 주입
- 태그 등록: influx_tag(레지스트리) + influx_qc_rule(알람 임계값) + viewer_tag(화면 표시)
- 모드: (default)무한루프 | once | backfill <days> [step_min]
- NUM_TAGS 환경변수로 태그 수 조정 (기본 100)
"""
import asyncio
import random
import os
import sys
from datetime import datetime, timedelta
import asyncpg
import pytz

# 한국 시간대
KST = pytz.timezone('Asia/Seoul')

# 실제 운영 센서 (tag_name, lo, hi, unit, tag_type) — dev DB snapshot 범위와 일치
SENSORS_REAL = [
    ("INLET_PRESSURE", 3.5, 4.2, "bar", "pressure"),
    ("FEED_COND", 950.0, 1020.0, "uS/cm", "conductivity"),
    ("PRODUCT_COND", 8.0, 11.0, "uS/cm", "conductivity"),
    ("FEED_FLOW", 48.0, 52.0, "m3/h", "flow"),
    ("PRODUCT_FLOW", 25.0, 30.0, "m3/h", "flow"),
]

# 합성 태그 카테고리 (이름prefix, lo, hi, unit, type) — 100태그 채우기용
CATEGORIES = [
    ("PRESSURE", 1.0, 10.0, "bar", "pressure"),
    ("FLOW", 10.0, 100.0, "m3/h", "flow"),
    ("COND", 5.0, 1200.0, "uS/cm", "conductivity"),
    ("TEMP", 15.0, 45.0, "C", "temperature"),
    ("LEVEL", 0.0, 100.0, "%", "level"),
    ("PH", 6.0, 8.5, "pH", "ph"),
    ("TURBIDITY", 0.0, 5.0, "NTU", "turbidity"),
    ("DO", 5.0, 12.0, "mg/L", "dissolved_oxygen"),
    ("ORP", 200.0, 600.0, "mV", "orp"),
    ("DPRESSURE", 0.1, 2.0, "bar", "pressure"),
]


def build_sensors(num_tags: int):
    """5 실제 + (num_tags-5) 합성 태그를 (name, lo, hi, unit, type)로 생성"""
    sensors = list(SENSORS_REAL)
    i = 1
    while len(sensors) < num_tags:
        prefix, lo, hi, unit, typ = CATEGORIES[(i - 1) % len(CATEGORIES)]
        span = hi - lo
        # 카테고리 내에서 인덱스마다 약간씩 범위를 변주
        base = lo + span * 0.1
        s_lo = round(base, 2)
        s_hi = round(base + span * 0.8, 2)
        sensors.append((f"{prefix}_{i:03d}", s_lo, s_hi, unit, typ))
        i += 1
    return sensors[:num_tags]


def qc_thresholds(lo: float, hi: float):
    """운영범위 [lo,hi] → (min_val, max_val, warning_low, warning_high, critical_low, critical_high)
    대시보드 status CASE: value<min_val|>max_val=critical(2), <warning_low|>warning_high=warning(1)."""
    span = hi - lo if hi > lo else 1.0
    return (
        lo,                      # min_val   (critical 하한)
        hi,                      # max_val   (critical 상한)
        round(lo + span * 0.10, 4),  # warning_low
        round(hi - span * 0.10, 4),  # warning_high
        round(lo - span * 0.10, 4),  # critical_low (참고)
        round(hi + span * 0.10, 4),  # critical_high (참고)
    )


NUM_TAGS = int(os.getenv("NUM_TAGS", "100"))
SENSORS = build_sensors(NUM_TAGS)

# PostgreSQL 연결 설정 (Docker vs Local)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": "postgres",
    "password": "postgres",
    "database": "ecoanp",
}


async def register_tags(conn):
    """태그를 influx_tag / influx_qc_rule / viewer_tag 에 등록 (idempotent)"""
    names = [s[0] for s in SENSORS]
    # 관리 대상 태그만 정리 후 재등록 (제약 없는 빈 테이블)
    await conn.execute("DELETE FROM influx_tag WHERE tag_name = ANY($1)", names)
    await conn.execute("DELETE FROM influx_qc_rule WHERE tag_name = ANY($1)", names)

    tag_rows = []
    qc_rows = []
    for name, lo, hi, unit, typ in SENSORS:
        tag_rows.append((name, name, name, typ, unit, f"{typ} sensor ({unit})"))
        mn, mx, wl, wh, cl, ch = qc_thresholds(lo, hi)
        qc_rows.append((name, mn, mx, wl, wh, cl, ch))

    await conn.executemany(
        """INSERT INTO influx_tag (key, tag_id, tag_name, tag_type, unit, description)
           VALUES ($1,$2,$3,$4,$5,$6)""",
        tag_rows,
    )
    await conn.executemany(
        """INSERT INTO influx_qc_rule
           (tag_name, min_val, max_val, warning_low, warning_high, critical_low, critical_high)
           VALUES ($1,$2,$3,$4,$5,$6,$7)""",
        qc_rows,
    )
    # viewer_tag: 화면 표시 (PK tag_name → upsert)
    await conn.executemany(
        """INSERT INTO viewer_tag (tag_name, display_order, show_dashboard, show_alarm, show_trend, show_model)
           VALUES ($1,$2,true,true,true,true)
           ON CONFLICT (tag_name) DO NOTHING""",
        [(s[0], (idx + 1) * 10) for idx, s in enumerate(SENSORS)],
    )
    print(f"[REGISTER] {len(SENSORS)} tags → influx_tag / influx_qc_rule / viewer_tag", flush=True)


def _gen_value(lo: float, hi: float) -> float:
    """운영범위보다 약간 넓게 생성 → 일부는 warning/critical 발생 (알람 검증용)"""
    span = hi - lo if hi > lo else 1.0
    return round(random.uniform(lo - span * 0.08, hi + span * 0.08), 2)


async def inject_data_once(conn=None):
    """현재 시각으로 전체 태그 1회 주입"""
    own = conn is None
    if own:
        conn = await asyncpg.connect(**DB_CONFIG)
    try:
        now = datetime.now(KST)
        rows = [(now, name, _gen_value(lo, hi), random.choice([0, 192]))
                for name, lo, hi, _u, _t in SENSORS]
        await conn.executemany(
            """INSERT INTO influx_hist (ts, tag_name, value, quality)
               VALUES ($1,$2,$3,$4)
               ON CONFLICT (ts, tag_name) DO UPDATE
               SET value = EXCLUDED.value, quality = EXCLUDED.quality""",
            rows,
        )
        print(f"[OK] {len(SENSORS)} sensors injected at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}", flush=True)
    finally:
        if own:
            await conn.close()


async def backfill(days: int, step_min: int = 1):
    """과거 days일치 데이터를 step_min분 간격으로 대량 적재 (perf/집계 검증용, COPY 사용)"""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        await register_tags(conn)
        now = datetime.now(KST).replace(second=0, microsecond=0)
        start = now - timedelta(days=days)
        total = 0
        # 태그별 부드러운 변동을 위해 현재값 상태 유지
        cur = {name: random.uniform(lo, hi) for name, lo, hi, _u, _t in SENSORS}
        batch = []
        t = start
        while t <= now:
            for name, lo, hi, _u, _t in SENSORS:
                span = hi - lo if hi > lo else 1.0
                # random walk (운영범위 근처서 천천히 변동, 가끔 이탈)
                cur[name] += random.uniform(-span * 0.05, span * 0.05)
                v = min(max(cur[name], lo - span * 0.1), hi + span * 0.1)
                batch.append((t, name, round(v, 2), 192))  # tz-aware (KST) → timestamptz
            if len(batch) >= 50000:
                await conn.copy_records_to_table(
                    "influx_hist", records=batch, columns=["ts", "tag_name", "value", "quality"])
                total += len(batch)
                print(f"[BACKFILL] {total} rows... ({t:%Y-%m-%d %H:%M})", flush=True)
                batch = []
            t += timedelta(minutes=step_min)
        if batch:
            await conn.copy_records_to_table(
                "influx_hist", records=batch, columns=["ts", "tag_name", "value", "quality"])
            total += len(batch)
        print(f"[BACKFILL DONE] {total} rows over {days}d × {len(SENSORS)} tags @ {step_min}min", flush=True)
    finally:
        await conn.close()


async def inject_data_loop(interval_seconds=300):
    """무한 루프 주입 (시작 시 태그 등록)"""
    print(f"[START] {len(SENSORS)} tags, inject every {interval_seconds // 60} min", flush=True)
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        await register_tags(conn)
    finally:
        await conn.close()
    while True:
        try:
            await inject_data_once()
            await asyncio.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n[STOP] Data injection stopped", flush=True)
            break
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            await asyncio.sleep(10)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        asyncio.run(inject_data_once())
    elif len(sys.argv) > 1 and sys.argv[1] == "backfill":
        _days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        _step = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        asyncio.run(backfill(_days, _step))
    else:
        asyncio.run(inject_data_loop(interval_seconds=300))
