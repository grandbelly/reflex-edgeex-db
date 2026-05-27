"""
State for sync monitoring page
동기화 모니터링 페이지 상태
"""

import reflex as rx
from typing import List, Dict, Any
from datetime import datetime, timedelta
import asyncio
from ksys_app.db import get_pool
from ksys_app.services.remote_db_service import RemoteDBConfig, RemoteDBService
from reflex.utils import console


class SyncMonitorState(rx.State):
    """State for monitoring remote DB synchronization"""

    # Data
    sync_statuses: List[Dict[str, Any]] = []
    recent_logs: List[Dict[str, Any]] = []
    total_tags: int = 0
    active_tags: int = 0
    records_24h: int = 0
    avg_delay: int = 0

    # UI state
    loading: bool = False
    auto_refresh: bool = False
    syncing_tags: bool = False
    syncing_realtime: bool = False
    syncing_historical: bool = False

    # Auto refresh handle
    _refresh_task: Any = None

    @rx.event(background=True)
    async def refresh_data(self):
        """Refresh monitoring data"""
        async with self:
            self.loading = True
            yield

        try:
            pool = await get_pool()

            async with pool.connection() as conn:
                async with conn.cursor() as cursor:
                    # Get sync status
                    await cursor.execute("""
                        SELECT
                            remote_system,
                            table_name,
                            last_sync_time,
                            last_sync_status,
                            last_sync_record_count,
                            total_synced_records,
                            CASE
                                WHEN last_sync_time > NOW() - INTERVAL '10 minutes' THEN '✅ 정상'
                                WHEN last_sync_time > NOW() - INTERVAL '1 hour' THEN '⚠️ 확인필요'
                                ELSE '❌ 중단됨'
                            END as health_status
                        FROM sync_status
                        ORDER BY last_sync_time DESC
                    """)

                    statuses = []
                    for row in await cursor.fetchall():
                        statuses.append({
                            'remote_system': row[0],
                            'table_name': row[1],
                            'last_sync_time': row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else 'Never',
                            'last_sync_status': row[3],
                            'last_sync_record_count': row[4] or 0,
                            'total_synced_records': row[5] or 0,
                            'health_status': row[6]
                        })

                    # Get recent logs
                    await cursor.execute("""
                        SELECT
                            table_name,
                            start_time,
                            status,
                            record_count
                        FROM sync_log
                        WHERE start_time > NOW() - INTERVAL '1 hour'
                        ORDER BY start_time DESC
                        LIMIT 20
                    """)

                    logs = []
                    for row in await cursor.fetchall():
                        logs.append({
                            'table_name': row[0],
                            'timestamp': row[1].strftime('%H:%M:%S'),
                            'status': row[2],
                            'record_count': row[3] or 0
                        })

                    # Get statistics
                    await cursor.execute("""
                        SELECT
                            COUNT(DISTINCT tag_name) as total_tags
                        FROM influx_tag
                        WHERE remote_system = 'exaxt_stp'
                    """)
                    total_tags = (await cursor.fetchone())[0] or 0

                    await cursor.execute("""
                        SELECT
                            COUNT(DISTINCT tag_name) as active_tags,
                            COUNT(*) as records_24h
                        FROM influx_hist
                        WHERE source = 'remote'
                          AND ts > NOW() - INTERVAL '24 hours'
                    """)
                    row = await cursor.fetchone()
                    active_tags = row[0] or 0
                    records_24h = row[1] or 0

                    # Calculate average delay
                    await cursor.execute("""
                        SELECT
                            EXTRACT(EPOCH FROM (NOW() - MAX(ts))) as delay_seconds
                        FROM influx_hist
                        WHERE source = 'remote'
                    """)
                    delay = await cursor.fetchone()
                    avg_delay = int(delay[0]) if delay and delay[0] else 0

            async with self:
                self.sync_statuses = statuses
                self.recent_logs = logs
                self.total_tags = total_tags
                self.active_tags = active_tags
                self.records_24h = records_24h
                self.avg_delay = avg_delay
                self.loading = False
                yield

        except Exception as e:
            console.log(f"Error refreshing sync monitor: {e}")
            async with self:
                self.loading = False
                yield

    @rx.event(background=True)
    async def sync_tags(self):
        """Manually sync tags"""
        async with self:
            self.syncing_tags = True
            yield

        try:
            # Run tag sync
            # Upstream IoT cloud DB — credentials externalized to .env
            # See .env.example for required vars: UPSTREAM_DB_HOST/PORT/NAME/USER/PASSWORD
            import os
            upstream_host = os.getenv("UPSTREAM_DB_HOST", "")
            upstream_user = os.getenv("UPSTREAM_DB_USER", "")
            upstream_password = os.getenv("UPSTREAM_DB_PASSWORD", "")
            if not (upstream_host and upstream_user and upstream_password):
                console.log("UPSTREAM_DB_* env vars not set — skipping tag sync. "
                            "Set them in .env to enable upstream tag sync.")
                async with self:
                    self.syncing_tags = False
                    yield
                return
            config = RemoteDBConfig(
                host=upstream_host,
                port=int(os.getenv("UPSTREAM_DB_PORT", "9543")),
                database=os.getenv("UPSTREAM_DB_NAME", "iot_cloud_v2_exaxt_stp"),
                username=upstream_user,
                password=upstream_password
            )

            async with RemoteDBService(config) as remote:
                tags = await remote.get_tag_config()
                console.log(f"Synced {len(tags)} tags")

            # Refresh display
            await self.refresh_data()

        except Exception as e:
            console.log(f"Error syncing tags: {e}")

        async with self:
            self.syncing_tags = False
            yield

    @rx.event(background=True)
    async def sync_realtime(self):
        """Manually sync realtime data"""
        async with self:
            self.syncing_realtime = True
            yield

        try:
            # This would call the sync_realtime_columnar script
            console.log("Realtime sync triggered")
            # Implementation would go here

            await self.refresh_data()

        except Exception as e:
            console.log(f"Error syncing realtime: {e}")

        async with self:
            self.syncing_realtime = False
            yield

    @rx.event(background=True)
    async def sync_historical(self):
        """Manually sync historical data"""
        async with self:
            self.syncing_historical = True
            yield

        try:
            # This would call the sync_columnar_data script
            console.log("Historical sync triggered")
            # Implementation would go here

            await self.refresh_data()

        except Exception as e:
            console.log(f"Error syncing historical: {e}")

        async with self:
            self.syncing_historical = False
            yield

    def toggle_auto_refresh(self):
        """Toggle auto refresh"""
        self.auto_refresh = not self.auto_refresh

        if self.auto_refresh:
            # Start auto refresh (would use asyncio task)
            console.log("Auto refresh enabled")
        else:
            # Stop auto refresh
            console.log("Auto refresh disabled")

    def on_load(self):
        """Called when page loads"""
        return SyncMonitorState.refresh_data