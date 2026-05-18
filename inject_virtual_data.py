"""
Virtual Data Injection Script
5분 간격으로 랜덤 센서 데이터를 PostgreSQL에 주입
"""
import asyncio
import random
import os
from datetime import datetime
import asyncpg
import pytz

# 한국 시간대
KST = pytz.timezone('Asia/Seoul')

# 센서 정의 (tag_name, min, max) — ranges chosen to match the dev DB snapshot
# observed in influx_hist for refactor-validation. (prod removed these tags
# 2025-12-27; this file is the local-fullstack injector.)
SENSORS = [
    ("INLET_PRESSURE", 3.5, 4.2),
    ("FEED_COND", 950, 1020),
    ("PRODUCT_COND", 8.0, 11.0),
    ("FEED_FLOW", 48.0, 52.0),
    ("PRODUCT_FLOW", 25.0, 30.0),
]

# PostgreSQL 연결 설정 (Docker vs Local)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),  # Docker: pgai-db / ksys-dev-db, Local: localhost
    "port": int(os.getenv("DB_PORT", "5432")),  # Docker: 5432, Local: 5432
    "user": "postgres",
    "password": "postgres",
    "database": "ecoanp"
}


async def inject_data_once():
    """한 번만 데이터 주입"""
    if not SENSORS:
        print("[SKIP] No sensors configured for injection", flush=True)
        return

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # 현재 시간 (KST)
        now = datetime.now(KST)

        # 각 센서별 데이터 생성
        for tag_name, min_val, max_val in SENSORS:
            value = round(random.uniform(min_val, max_val), 2)
            quality = random.choice([0, 192])  # Good quality

            # INSERT with ON CONFLICT
            await conn.execute("""
                INSERT INTO influx_hist (ts, tag_name, value, quality)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (ts, tag_name) DO UPDATE
                SET value = EXCLUDED.value, quality = EXCLUDED.quality
            """, now, tag_name, value, quality)

        print(f"[OK] {len(SENSORS)} sensors injected at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}", flush=True)

    finally:
        await conn.close()


async def inject_data_loop(interval_seconds=300):
    """5 minute interval data injection (infinite loop)"""
    print(f"[START] Virtual data injection every {interval_seconds//60} minutes", flush=True)

    while True:
        try:
            await inject_data_once()
            print(f"[INFO] Next injection in {interval_seconds} seconds...", flush=True)
            await asyncio.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n[STOP] Data injection stopped", flush=True)
            break
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            await asyncio.sleep(10)  # Wait 10 sec on error


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "once":
        # 한 번만 실행
        asyncio.run(inject_data_once())
    else:
        # 5분 간격 무한 반복
        asyncio.run(inject_data_loop(interval_seconds=300))
