from __future__ import annotations

import os
import sys
import asyncio
import logging
import asyncpg
from typing import Any
from edgeex_app.utils.logger import get_logger, log_function

# Initialize logger for this module
logger = get_logger(__name__)

# Windows에서 ProactorEventLoop 문제 해결 (로컬 개발 환경에서만)
# Docker 환경에서는 Linux이므로 이 설정이 필요 없음
if sys.platform == 'win32' and not os.environ.get('DOCKER_CONTAINER'):
    logger.info("Setting WindowsSelectorEventLoopPolicy for Windows environment")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    logger.info(f"Running on platform: {sys.platform}, Docker: {os.environ.get('DOCKER_CONTAINER', 'False')}")


def _normalize_sql_placeholders(sql: str) -> str:
    """psycopg 스타일 위치 지정자(%s)를 asyncpg 위치 지정자($1, $2, ...)로 자동 변환."""
    if "%s" not in sql:
        return sql
    parts = sql.split("%s")
    out = [parts[0]]
    for idx, part in enumerate(parts[1:], start=1):
        out.append(f"${idx}")
        out.append(part)
    return "".join(out)


@log_function
def _dsn() -> str:
    dsn = os.environ.get("TS_DSN", "")
    if not dsn:
        logger.error("TS_DSN is not set in environment")
        raise RuntimeError("TS_DSN is not set in environment")
    logger.debug(f"DSN retrieved: {dsn[:30]}...")  # Log only first 30 chars for security
    return dsn


# 글로벌 풀 변수 (이벤트 루프별 바인딩 추적)
_GLOBAL_POOL: asyncpg.Pool | None = None
_POOL_LOOP: asyncio.AbstractEventLoop | None = None
_POOL_LOCK: asyncio.Lock | None = None


@log_function
async def get_pool() -> asyncpg.Pool:
    """글로벌 싱글톤 풀 관리 (이벤트 루프 변경 시 안전하게 재생성)"""
    global _GLOBAL_POOL, _POOL_LOOP, _POOL_LOCK

    current_loop = asyncio.get_running_loop()
    if _POOL_LOCK is None or _POOL_LOOP is not current_loop:
        _POOL_LOCK = asyncio.Lock()

    if _GLOBAL_POOL is None or _POOL_LOOP is not current_loop or getattr(_GLOBAL_POOL, "_closed", False):
        async with _POOL_LOCK:
            if _GLOBAL_POOL is None or _POOL_LOOP is not current_loop or getattr(_GLOBAL_POOL, "_closed", False):
                pid = os.getpid()
                logger.info(f"Creating global pool in process {pid}")
                try:
                    _GLOBAL_POOL = await asyncpg.create_pool(
                        _dsn(),
                        min_size=1,
                        max_size=10,
                        timeout=60.0,
                        command_timeout=60.0,
                    )
                    _POOL_LOOP = current_loop
                    logger.info(f"Global pool created successfully (PID: {pid})")
                except Exception as e:
                    logger.error(f"Failed to create global pool: {str(e)}")
                    _GLOBAL_POOL = None
                    _POOL_LOOP = None
                    raise

    return _GLOBAL_POOL


@log_function
async def q(sql: str, params: tuple | dict = (), timeout: float = 60.0):
    """쿼리 실행 - 글로벌 풀 사용"""
    start_time = asyncio.get_running_loop().time()
    normalized_sql = _normalize_sql_placeholders(sql)

    if isinstance(params, dict):
        params = tuple(params.values()) if params else ()

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            results = await conn.fetch(normalized_sql, *params, timeout=timeout)
            results = [dict(row) for row in results]

            elapsed = asyncio.get_running_loop().time() - start_time
            if elapsed > 1.0:
                logger.warning(f"Slow query ({elapsed:.2f}s): {normalized_sql[:100]}...")
            elif logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Query completed in {elapsed:.3f}s, returned {len(results)} rows")

            return results

    except asyncio.TimeoutError as e:
        logger.warning(f"Pool timeout, using direct connection: {str(e)}")
        try:
            conn = await asyncpg.connect(_dsn())
            try:
                results = await conn.fetch(normalized_sql, *params, timeout=timeout)
                results = [dict(row) for row in results]
                elapsed = asyncio.get_running_loop().time() - start_time
                logger.info(f"Direct connection query completed in {elapsed:.3f}s")
                return results
            finally:
                await conn.close()
        except Exception as e2:
            logger.error(f"Direct connection also failed: {str(e2)}")
            raise

    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        logger.error(f"SQL: {normalized_sql}")
        logger.error(f"Params: {params}")
        raise


@log_function
async def execute_query(sql: str, params: tuple | dict = (), timeout: float = 60.0):
    """Execute SQL without expecting results (for INSERT, UPDATE, DELETE)"""
    start_time = asyncio.get_running_loop().time()
    normalized_sql = _normalize_sql_placeholders(sql)

    if isinstance(params, dict):
        params = tuple(params.values()) if params else ()

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(normalized_sql, *params, timeout=timeout)
            elapsed = asyncio.get_running_loop().time() - start_time
            if elapsed > 1.0:
                logger.warning(f"Slow execute ({elapsed:.2f}s): {normalized_sql[:100]}...")
            elif logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Execute completed in {elapsed:.3f}s")

    except asyncio.TimeoutError as e:
        logger.warning(f"Pool timeout, using direct connection for execute: {str(e)}")
        try:
            conn = await asyncpg.connect(_dsn())
            try:
                await conn.execute(normalized_sql, *params, timeout=timeout)
                elapsed = asyncio.get_running_loop().time() - start_time
                logger.info(f"Direct connection execute completed in {elapsed:.3f}s")
            finally:
                await conn.close()
        except Exception as e2:
            logger.error(f"Direct connection execute also failed: {str(e2)}")
            raise

    except Exception as e:
        logger.error(f"Execute query failed: {str(e)}")
        logger.error(f"SQL: {normalized_sql}")
        logger.error(f"Params: {params}")
        raise


async def close_pool():
    """풀 정리"""
    global _GLOBAL_POOL, _POOL_LOOP

    if _GLOBAL_POOL is not None:
        try:
            await _GLOBAL_POOL.close()
            _GLOBAL_POOL = None
            _POOL_LOOP = None
            logger.info("Global pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing pool: {e}")
