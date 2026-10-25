"""
Seed a single AutoARIMA model into model_registry so the forecast-scheduler
refactor paths exercise end-to-end against the local stack.

Run inside the reflex-app container:
    docker exec edgeex-local-reflex-app python -m edgeex_app.scripts.seed_fake_model

The script:
1. Pulls the last 7 days of INLET_PRESSURE from influx_hist (10-min resampled).
2. Fits AutoARIMAPlugin on that window (≈1000 points).
3. pickle.dumps(plugin) → BYTEA.
4. INSERTs a row into model_registry with is_deployed=TRUE / is_active=TRUE
   and a pipeline_config that matches the forecast scheduler's expectations.

Idempotent: deletes any existing row with model_name='seed_autoarima_inlet_pressure'
before inserting.
"""
from __future__ import annotations

import asyncio
import json
import os
import pickle
import sys
import time

import pandas as pd

from edgeex_app.ml.pipeline_v2_hybrid import AutoARIMAPlugin
from edgeex_app.db_orm import get_async_session
from sqlalchemy import text


TAG = "INLET_PRESSURE"
MODEL_NAME = "seed_autoarima_inlet_pressure"
MODEL_TYPE = "AUTO_ARIMA"
VERSION = "v0.1-seed"

# Cycle config the scheduler reads from pipeline_config.forecast_config
HORIZONS_MIN = [60, 120, 360, 720, 1440]


async def fetch_training_window(session) -> pd.DataFrame:
    print(f"[seed] fetching last 24h of available {TAG} data from influx_hist...", flush=True)
    # Use the dataset's own latest timestamp as the anchor — the dev DB
    # holds a frozen snapshot whose 'now()' is months in the past.
    # 24h × 10-min buckets = 144 points; AutoARIMA fit ~30s.
    q = text("""
        WITH anchor AS (
            SELECT max(ts) AS latest FROM influx_hist WHERE tag_name = :tag
        )
        SELECT date_trunc('minute', ts) - (EXTRACT(minute FROM ts)::int % 10) * interval '1 minute' AS bucket,
               avg(value)::float AS value
          FROM influx_hist, anchor
         WHERE tag_name = :tag
           AND ts > anchor.latest - interval '1 day'
         GROUP BY bucket
         ORDER BY bucket
    """)
    rs = await session.execute(q, {"tag": TAG})
    rows = rs.fetchall()
    if not rows:
        raise RuntimeError(f"no data for tag {TAG} in influx_hist")
    df = pd.DataFrame(rows, columns=["timestamp", "value"]).dropna()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    print(f"[seed] got {len(df)} points, range {df['timestamp'].min()} → {df['timestamp'].max()}")
    return df


async def upsert_model_row(session, model_bytes: bytes, samples: int) -> int:
    pipeline_config = {
        "forecast_config": {
            "horizons": HORIZONS_MIN,
            "forecast_interval_minutes": 10,
            "forecast_horizon_hours": 24,
        }
    }
    feature_config = {"freq": "10T", "season_length": 144}

    await session.execute(
        text("DELETE FROM model_registry WHERE model_name = :name"),
        {"name": MODEL_NAME},
    )
    res = await session.execute(
        text("""
            INSERT INTO model_registry
                (model_name, model_type, version, tag_name,
                 hyperparameters, feature_config,
                 model_path, model_size_bytes,
                 training_samples,
                 is_active, is_deployed, deployed_at, deployed_by,
                 pipeline_config, model_pickle, created_by)
            VALUES (:name, :mtype, :ver, :tag,
                    CAST(:hp AS jsonb), CAST(:fc AS jsonb),
                    NULL, :sz,
                    :samples,
                    TRUE, TRUE, now() AT TIME ZONE 'UTC', 'seed-script',
                    CAST(:pc AS jsonb), :pkl, 'seed-script')
            RETURNING model_id
        """),
        {
            "name": MODEL_NAME,
            "mtype": MODEL_TYPE,
            "ver": VERSION,
            "tag": TAG,
            "hp": json.dumps({"season_length": 24}),
            "fc": json.dumps(feature_config),
            "sz": len(model_bytes),
            "samples": samples,
            "pc": json.dumps(pipeline_config),
            "pkl": model_bytes,
        },
    )
    model_id = res.scalar_one()
    await session.commit()
    return model_id


async def main():
    os.environ.setdefault("PYTHONUTF8", "1")

    async with get_async_session() as session:
        df = await fetch_training_window(session)

    plugin = AutoARIMAPlugin(season_length=24)
    print("[seed] fitting AutoARIMA on 1 day @ 10min (~30s)...", flush=True)
    t0 = time.perf_counter()
    await plugin.train(df)
    fit_s = time.perf_counter() - t0
    print(f"[seed] fit done in {fit_s:.1f}s, info={plugin.model_info.get('arima_string', '?')}")

    model_bytes = pickle.dumps(plugin)
    print(f"[seed] pickled plugin: {len(model_bytes):,} bytes")

    async with get_async_session() as session:
        model_id = await upsert_model_row(session, model_bytes, samples=len(df))
    print(f"[seed] inserted model_id={model_id} as is_deployed=TRUE, is_active=TRUE")


if __name__ == "__main__":
    asyncio.run(main())
