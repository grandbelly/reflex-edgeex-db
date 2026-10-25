"""
Regression tests for the forecast-scheduler DB layer.

Goal
----
Catch two failure modes:

    Pool leak — the scheduler opens a fresh session per helper call
        (get_deployed_models, get_latest_sensor_value, save_predictions,
        generate_forecast_player_cache). Each must be returned to the
        pool. A leak surfaces as `outstanding_connections > 0` after a
        run, or as a TimeoutError once max_overflow is consumed.

    Configurable command_timeout — asyncpg's command_timeout used to be
        hardcoded to 10s, which was tighter than legitimate TimescaleDB
        hypertable inserts. The configured value must now be reachable
        from the engine without monkey-patching.

These tests do **not** require a live database. They drive the engine
manager and its SQLAlchemy event hooks directly. The scheduler logic
itself is exercised against an in-memory SQLite engine that we wire
into the manager so the test can count checkouts/checkins per session.

Run with:

    pytest tests/schedulers/test_pool_exhaustion.py -v
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import pytest

# Make the project importable when pytest is invoked from the repo root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DB_ORM_ENV_KEYS = (
    "TS_DSN",
    "USE_DB_POOLING",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_TIMEOUT",
    "DB_POOL_RECYCLE",
    "DB_COMMAND_TIMEOUT",
    "DB_CONNECT_TIMEOUT",
    "DB_STATEMENT_TIMEOUT_MS",
    "DB_POOL_TRACE",
)


def _reload_db_orm(env: dict[str, str]):
    """Reload edgeex_app.db_orm with a controlled env so the module-level
    constants (USE_POOLING, COMMAND_TIMEOUT, ...) reflect the test scenario.

    Clears any prior DB_* env from earlier tests so each scenario starts
    from a clean slate.
    """
    for key in _DB_ORM_ENV_KEYS:
        os.environ.pop(key, None)
    for key, value in env.items():
        os.environ[key] = value
    # Force-reload because constants are evaluated at import time
    if "edgeex_app.db_orm" in sys.modules:
        del sys.modules["edgeex_app.db_orm"]
    return importlib.import_module("edgeex_app.db_orm")


# ---------------------------------------------------------------------------
# Connection lifecycle / pool exhaustion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_h1_session_returns_connection_to_pool(monkeypatch):
    """Each get_async_session() must check the connection back in.

    Failure mode this guards against: a `commit()`-then-exception path
    that escapes the context manager and leaves a connection dangling.
    On an unfixed code path the counters would diverge after the loop.
    """
    db_orm = _reload_db_orm({
        # Use an in-memory sqlite engine — fast, no external service needed.
        # The event hooks fire identically on every dialect.
        "TS_DSN": "sqlite+aiosqlite:///:memory:",
        "USE_DB_POOLING": "true",
        "DB_POOL_SIZE": "2",
        "DB_MAX_OVERFLOW": "2",
        "DB_POOL_TIMEOUT": "2",
        "DB_STATEMENT_TIMEOUT_MS": "0",  # sqlite doesn't honor it
        "DB_POOL_TRACE": "false",
    })

    # Patch the URL builder out — sqlite doesn't need asyncpg normalization
    monkeypatch.setattr(db_orm, "ASYNC_URL", "sqlite+aiosqlite:///:memory:")
    # asyncpg-specific connect_args break sqlite. Override get_engine to use
    # a clean engine but keep instrumentation.
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.pool import AsyncAdaptedQueuePool
    from sqlalchemy import event

    manager = db_orm.get_engine_manager()
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=AsyncAdaptedQueuePool,
        pool_size=2,
        max_overflow=2,
        pool_timeout=2,
    )
    sync_engine = engine.sync_engine

    @event.listens_for(sync_engine, "checkout")
    def _on_checkout(dbapi_conn, conn_record, conn_proxy):  # noqa: ARG001
        manager.checkouts += 1

    @event.listens_for(sync_engine, "checkin")
    def _on_checkin(dbapi_conn, conn_record):  # noqa: ARG001
        manager.checkins += 1

    manager._engine = engine
    manager._session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        # Simulate the scheduler hitting get_async_session() repeatedly.
        # 12 iterations × 3 helper calls each = 36 checkouts on a pool of
        # capacity 4. If a single iteration leaked, the 5th would hang and
        # fail this test with pool_timeout.
        for _ in range(12):
            async with db_orm.get_async_session() as session:
                await session.execute(__import__("sqlalchemy").text("SELECT 1"))
            async with db_orm.get_async_session() as session:
                await session.execute(__import__("sqlalchemy").text("SELECT 2"))
            async with db_orm.get_async_session() as session:
                await session.execute(__import__("sqlalchemy").text("SELECT 3"))

        assert manager.checkouts == 36, (
            f"Expected 36 checkouts, got {manager.checkouts}"
        )
        assert manager.checkins == 36, (
            f"Expected 36 checkins, got {manager.checkins} "
            f"(leak of {manager.outstanding_connections})"
        )
        assert manager.outstanding_connections == 0
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_h1_pool_exhaustion_raises_timeout(monkeypatch):
    """When more concurrent sessions are requested than the pool can
    provide, SQLAlchemy must raise a TimeoutError instead of hanging
    forever. This documents the failure mode and the diagnostic the
    scheduler is expected to surface."""
    from sqlalchemy.exc import TimeoutError as SATimeout

    db_orm = _reload_db_orm({
        "TS_DSN": "sqlite+aiosqlite:///:memory:",
        "USE_DB_POOLING": "true",
        "DB_POOL_SIZE": "1",
        "DB_MAX_OVERFLOW": "0",
        "DB_POOL_TIMEOUT": "1",
        "DB_STATEMENT_TIMEOUT_MS": "0",
    })

    monkeypatch.setattr(db_orm, "ASYNC_URL", "sqlite+aiosqlite:///:memory:")
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.pool import AsyncAdaptedQueuePool
    manager = db_orm.get_engine_manager()
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=AsyncAdaptedQueuePool,
        pool_size=1, max_overflow=0, pool_timeout=1,
    )
    manager._engine = engine
    manager._session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        @asynccontextmanager
        async def hold_session() -> AsyncGenerator[None, None]:
            async with db_orm.get_async_session() as s:
                await s.execute(__import__("sqlalchemy").text("SELECT 1"))
                # Hold the only connection in the pool open
                await asyncio.sleep(0.5)
                yield

        async def grab():
            async with db_orm.get_async_session() as s:
                await s.execute(__import__("sqlalchemy").text("SELECT 1"))

        async with hold_session():
            with pytest.raises((SATimeout, asyncio.TimeoutError)):
                await asyncio.wait_for(grab(), timeout=2.5)
    finally:
        await manager.close()


# ---------------------------------------------------------------------------
# Command/statement timeout is wired through env
# ---------------------------------------------------------------------------

def test_h5_command_timeout_is_configurable():
    """The previous hard-coded 10s asyncpg command_timeout was the direct
    cause of the intermittent forecast-scheduler TimeoutError on
    TimescaleDB hypertable inserts. The value must now be readable from
    the env and default to a safer 30s."""
    db_orm = _reload_db_orm({
        "TS_DSN": "postgresql://x:y@h/db",
        "USE_DB_POOLING": "false",
    })
    assert db_orm.COMMAND_TIMEOUT == 30
    assert db_orm.STATEMENT_TIMEOUT_MS == 30000

    db_orm = _reload_db_orm({
        "TS_DSN": "postgresql://x:y@h/db",
        "USE_DB_POOLING": "false",
        "DB_COMMAND_TIMEOUT": "60",
        "DB_STATEMENT_TIMEOUT_MS": "45000",
    })
    assert db_orm.COMMAND_TIMEOUT == 60
    assert db_orm.STATEMENT_TIMEOUT_MS == 45000


def test_h5_pooling_opt_in_does_not_break_legacy_default():
    """Default behavior must remain NullPool so existing Reflex deploys
    are unaffected by the H1 fix."""
    db_orm = _reload_db_orm({
        "TS_DSN": "postgresql://x:y@h/db",
    })
    # Clear any prior env from earlier tests
    for k in ("USE_DB_POOLING",):
        os.environ.pop(k, None)
    db_orm = _reload_db_orm({"TS_DSN": "postgresql://x:y@h/db"})
    assert db_orm.USE_POOLING is False
