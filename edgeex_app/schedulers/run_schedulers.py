#!/usr/bin/env python3
"""
Standalone Forecasting Schedulers Service.

- ForecastScheduler: every 10 minutes (online predictions)
- ActualValueUpdater: every 10 minutes (fills actual values)
- PerformanceAggregator: every 1 hour (metrics)

Signal handling: SIGTERM/SIGINT cancel the main task so the finally block
runs stop_all_schedulers() for graceful cleanup. Without this, docker stop
waits the grace period then SIGKILLs, leaking socket listeners.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from edgeex_app.schedulers.scheduler_manager import (
    start_all_schedulers,
    stop_all_schedulers,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("=" * 80)
    logger.info("🚀 FORECASTING SCHEDULERS SERVICE STARTING")
    logger.info("=" * 80)
    logger.info("  - ForecastScheduler:    every 10 min (x:00)")
    logger.info("  - ActualValueUpdater:   every 10 min (x:01)")
    logger.info("  - PerformanceAggregator: every 1 hour (x:03)")
    logger.info("=" * 80)

    loop = asyncio.get_running_loop()
    main_task = asyncio.current_task()

    def _request_shutdown(signame):
        logger.info("=" * 80)
        logger.info(f"🛑 Received {signame}, cancelling main task for graceful shutdown")
        logger.info("=" * 80)
        if not main_task.done():
            main_task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown, sig.name)
        except NotImplementedError:
            # Windows event loop doesn't support add_signal_handler for SIGTERM;
            # signal.signal works for SIGINT only.
            signal.signal(sig, lambda s, f: main_task.cancel())

    try:
        await start_all_schedulers()
    except asyncio.CancelledError:
        logger.info("Main task cancelled — proceeding to graceful shutdown")
    except Exception as e:
        logger.error(f"❌ Fatal error in scheduler service: {e}", exc_info=True)
        return 1
    finally:
        logger.info("🧹 Stopping schedulers (graceful)...")
        try:
            await asyncio.wait_for(stop_all_schedulers(), timeout=15.0)
            logger.info("✅ Schedulers stopped gracefully")
        except asyncio.TimeoutError:
            logger.error("⚠️ Scheduler shutdown timed out after 15s")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
        logger.info("=" * 80)
        logger.info("👋 Forecasting Schedulers Service Exited")
        logger.info("=" * 80)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(0)
