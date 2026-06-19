import reflex as rx
import os
import sys
import logging
import traceback
import asyncio
from pathlib import Path
from ksys_app.utils.logger import get_logger, log_function, LogOperation, setup_logging

# Setup logging first
setup_logging()
logger = get_logger(__name__)

# Global exception handler to catch ALL errors
def handle_exception(exc_type, exc_value, exc_traceback):
    """Log all uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    logger.error(f"Exception Type: {exc_type.__name__}")
    logger.error(f"Exception Value: {exc_value}")
    logger.error(f"Traceback:\n{''.join(traceback.format_tb(exc_traceback))}")

# Install exception handler
sys.excepthook = handle_exception

# Load environment variables from .env file
@log_function
def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    logger.info(f"Loading .env from: {env_path}")

    with LogOperation("load_environment_variables", logger):
        if env_path.exists():
            with open(env_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        os.environ[key] = value
                        # Mask sensitive values in logs
                        masked_value = '***' if any(s in key.lower() for s in ['password', 'dsn', 'key', 'secret']) else value
                        logger.debug(f"Loaded env var: {key}={masked_value}")
        else:
            logger.error(f".env file not found at {env_path}")

        # 중요한 환경변수 확인
        ts_dsn = os.getenv('TS_DSN')
        if ts_dsn:
            logger.info("TS_DSN is loaded successfully")
        else:
            logger.error("TS_DSN is not set!")

logger.info("="*80)
logger.info("STARTING KSYS APPLICATION")
logger.info("="*80)
load_env()

# Initialize database pool on startup
import asyncio
from .db import get_pool

@log_function
async def init_database_pool():
    """Initialize database connection pool on startup"""
    with LogOperation("database_pool_initialization", logger):
        try:
            pool = await get_pool()
            logger.info("Database pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
# Run pool initialization on startup
logger.info("Initializing database pool...")
try:
    asyncio.run(init_database_pool())
    logger.info("Database pool initialization completed")
except RuntimeError as e:
    # If event loop is already running, schedule the task
    logger.warning(f"RuntimeError during pool init: {e}")
    logger.info("Scheduling pool initialization in existing event loop")
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(init_database_pool())
    except Exception as inner_e:
        logger.error(f"Failed to schedule pool init: {inner_e}")
except Exception as e:
    logger.error(f"Unexpected error during pool initialization: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    # Don't raise - let the app continue
except Exception as e:
    print(f"[WARNING] Could not initialize pool on startup: {e}")

# Refresh materialized view on app startup
import psycopg

def refresh_materialized_views():
    """Refresh materialized views on startup and periodically"""
    # Technical indicators removed - no views to refresh
    pass

# Run refresh on startup
try:
    refresh_materialized_views()
except:
    pass  # Don't fail app startup if refresh fails

# 보안 기능 추가 (충돌 해결)
try:
    from .security import validate_startup_security, get_csp_headers
    # 애플리케이션 시작시 보안 검증
    validate_startup_security()
except ImportError:
    # 보안 모듈이 없으면 경고만 출력
    logging.warning("[WARNING] 보안 모듈을 찾을 수 없습니다. 보안 검증을 건너뜁니다.")
except Exception as e:
    logging.error(f"🚨 보안 검증 실패: {e}", exc_info=True)
    # 개발환경에서는 계속 진행, 운영환경에서는 중단 고려



app = rx.App(
    # RO control-room theme — dark instrument console (frontend-design).
    theme=rx.theme(
        appearance="dark",
        accent_color="teal",   # instrument aqua/permeate
        gray_color="slate",
        radius="medium",
        scaling="100%",
    ),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap&crossorigin=anonymous",
        "/styles.css",
    ],
    style={
        rx.el.body: {
            "font_family": "Inter, sans-serif",
        }
    },
    head_components=[
        # Control-room app has no theme toggle — pin dark so prior visitors
        # who still have `theme: light` in localStorage also get the new theme.
        rx.script(
            "try{localStorage.setItem('theme','dark');"
            "localStorage.removeItem('chakra-ui-color-mode');}catch(e){}"
        ),
    ],
)

# NOTE: Virtual Tag scheduler runs as a separate process
# To start the scheduler:
#   docker exec reflex-ksys-app python ksys_app/schedulers/virtual_tag_scheduler.py
# Or set up as a systemd service or cron job for production
# Main dashboard is loaded via @rx.page decorator in pages/dashboard.py
# Enhanced Trend page (/trend) — registered via @rx.page in pages/trend_enhanced_v2.py



# AI features - controlled by ENABLE_AI_FEATURES environment variable
ENABLE_AI_FEATURES = os.getenv('ENABLE_AI_FEATURES', 'true').lower() == 'true'
logger.info(f"AI Features: {'ENABLED' if ENABLE_AI_FEATURES else 'DISABLED'}")

# ============================================================================
# Page registration — every page uses @rx.page decorator inside its module.
# Import alone triggers registration; no app.add_page() calls needed.
# ============================================================================
from .pages import (
    alarms,                  # /alarms
    alarms_hist_new,         # /alarms_hist_new
    alarms_hist_simple,      # /alarms_hist
    alarms_rt_new,           # /alarms_rt_new
    alarms_rt_simple,        # /alarms_rt (@rx.page in module)
    communication,           # /comm
    dashboard,               # / (@rx.page in module)
    forecast_player,         # /forecast
    model_performance,       # /model-performance (@rx.page in module)
    scada_alarm_comparison,  # /scada-alarm-comparison
    scada_alarm_viewer,      # /scada-alarms
    training_wizard,         # /training-wizard (@rx.page in module)
    trend_enhanced_v2,       # /trend
    viewer_tag,              # /viewer-tag (@rx.page in module)
    workflow,                # /workflow (@rx.page in module)
)

# /ai (CR-01 등록 2026-06-03) — 별도 가드 import.
# ai_insights → ai_state → ai_engine.rag_engine 는 top-level 에서 openai/sklearn/numpy 를
# import 하므로, 이 패키지가 없는 이미지에서 무가드 import 하면 앱 전체 부팅이 죽는다.
# ENABLE_AI_FEATURES 플래그 + try/except 로 이중 가드: 비활성이거나 의존성 누락 시
# /ai 만 등록 생략하고 나머지 사이트는 정상 부팅한다.
if ENABLE_AI_FEATURES:
    try:
        from .pages import ai_insights  # noqa: F401  /ai (@rx.page in module)
        logger.info("AI page /ai registered")
    except Exception as e:
        logger.warning(f"/ai page skipped — AI 의존성 로드 실패 (openai/sklearn/numpy 확인): {e}")
else:
    logger.info("/ai page skipped — ENABLE_AI_FEATURES=false")

# ============================================================================
# Start Forecasting Schedulers (Phase 2 Implementation)
# ============================================================================
# Schedulers automatically generate online predictions for deployed models:
# - ForecastScheduler: Every 5 minutes (generates predictions)
# - ActualValueUpdater: Every 10 minutes (fills actual values)
# - PerformanceAggregator: Every 1 hour (calculates accuracy metrics)
#
# Schedulers are started via SchedulerState on app mount (see below)
# Architecture Reference: docs/forecast_result/ONLINE_FORECAST_REDESIGN_20251014.md
# ============================================================================

# Import scheduler state for lifecycle management
from .states.scheduler_state import SchedulerState

logger.info("="*80)
logger.info("SCHEDULER INITIALIZATION: Will start on app mount via SchedulerState")
logger.info("="*80)
