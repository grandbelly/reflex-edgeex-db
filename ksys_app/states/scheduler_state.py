"""
Scheduler State - Manages forecasting schedulers lifecycle within Reflex app.

By default the schedulers run as background tasks within Reflex. Set
DISABLE_INAPP_SCHEDULER=true when a separate scheduler container handles
forecasting so the in-app loop doesn't double-fire (e.g. local docker
fullstack with the dedicated forecast-scheduler service).
"""

import os
import reflex as rx
from reflex.utils import console
from ..schedulers import start_all_schedulers, stop_all_schedulers


def _inapp_scheduler_disabled() -> bool:
    return os.environ.get("DISABLE_INAPP_SCHEDULER", "false").lower() == "true"


class SchedulerState(rx.State):
    """State to manage forecasting schedulers within Reflex app"""

    schedulers_running: bool = False
    scheduler_error: str = ""

    @rx.event(background=True)
    async def start_schedulers(self):
        """Start all forecasting schedulers in background"""
        if _inapp_scheduler_disabled():
            console.log("In-app scheduler disabled via DISABLE_INAPP_SCHEDULER=true")
            async with self:
                self.schedulers_running = False
                self.scheduler_error = ""
            return
        try:
            console.log("=" * 80)
            console.log("🚀 Starting Forecasting Schedulers from State...")
            console.log("=" * 80)

            async with self:
                self.schedulers_running = True
                self.scheduler_error = ""

            # Start all schedulers (this runs indefinitely)
            await start_all_schedulers()

        except Exception as e:
            console.error(f"❌ Scheduler error in State: {e}")
            async with self:
                self.schedulers_running = False
                self.scheduler_error = str(e)

    async def stop_schedulers(self):
        """Stop all schedulers gracefully"""
        try:
            console.log("🛑 Stopping schedulers...")
            await stop_all_schedulers()

            self.schedulers_running = False
            self.scheduler_error = ""
            console.log("✅ Schedulers stopped")

        except Exception as e:
            console.error(f"❌ Error stopping schedulers: {e}")
            self.scheduler_error = str(e)
