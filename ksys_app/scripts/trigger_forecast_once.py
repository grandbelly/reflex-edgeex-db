"""
Manually trigger ForecastScheduler.run_once() once, bypassing the x:00/x:10
clock alignment so refactor paths can be exercised on demand.

Run inside the forecast-scheduler container:
    docker exec ksys-local-forecast-scheduler python -m ksys_app.scripts.trigger_forecast_once
"""
from __future__ import annotations

import asyncio
import logging

from ksys_app.schedulers.forecast_scheduler import ForecastScheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)


async def main():
    scheduler = ForecastScheduler()
    print("[trigger] firing one run_once cycle (10-min budget)")
    await scheduler.run_once(interval_seconds=600)
    print("[trigger] cycle complete")


if __name__ == "__main__":
    asyncio.run(main())
