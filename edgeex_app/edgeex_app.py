import reflex as rx
import os
import sys
import logging
import traceback
import asyncio
from pathlib import Path
from edgeex_app.utils.logger import get_logger, log_function, LogOperation, setup_logging

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

# Load environment variables from .env file (without overriding existing env vars)
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
                        # Preserve explicitly provided environment variables
                        os.environ.setdefault(key, value)
                        masked_value = '***' if any(s in key.lower() for s in ['password', 'dsn', 'key', 'secret']) else os.environ.get(key, value)
                        logger.debug(f"Loaded env var: {key}={masked_value}")
        else:
            logger.info(f".env file not found at {env_path}; using process environment variables")

        # 중요한 환경변수 확인
        ts_dsn = os.getenv('TS_DSN')
        if ts_dsn:
            logger.info("TS_DSN is loaded successfully")
        else:
            logger.error("TS_DSN is not set!")

logger.info("="*80)
logger.info("STARTING edgeEX APPLICATION")
logger.info("="*80)
load_env()

# Initialize database pool on startup
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

logger.info("Initializing database pool...")
try:
    asyncio.run(init_database_pool())
    logger.info("Database pool initialization completed")
except RuntimeError as e:
    logger.warning(f"RuntimeError during pool init: {e}")
    logger.info("Scheduling pool initialization in existing event loop")
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(init_database_pool())
    except Exception as inner_e:
        logger.error(f"Failed to schedule pool init: {inner_e}")
except Exception as e:
    logger.error(f"Unexpected error during pool initialization: {e}")

# Refresh materialized view on app startup
def refresh_materialized_views():
    """Refresh materialized views on startup and periodically"""
    pass

try:
    refresh_materialized_views()
except Exception:
    pass

# 보안 기능 추가
try:
    from .security import validate_startup_security, get_csp_headers
    validate_startup_security()
except ImportError:
    logging.warning("[WARNING] 보안 모듈을 찾을 수 없습니다. 보안 검증을 건너뜁니다.")
except Exception as e:
    logging.error(f"[SECURITY] 보안 검증 실패: {e}", exc_info=True)


app = rx.App(
    theme=rx.theme(
        appearance="inherit",
        accent_color="teal",
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
        rx.script(
            "try{if(!localStorage.getItem('theme')){localStorage.setItem('theme','dark');}"
            "localStorage.removeItem('chakra-ui-color-mode');}catch(e){}"
        ),
    ],
)

# AI features - controlled by ENABLE_AI_FEATURES environment variable
from .scada_config import scada_enabled
ENABLE_AI_FEATURES = os.getenv('ENABLE_AI_FEATURES', 'true').lower() == 'true' and not scada_enabled()
if os.getenv("APP_VERSION", "FULL").upper() == "PART":
    ENABLE_AI_FEATURES = False
logger.info(f"AI Features: {'ENABLED' if ENABLE_AI_FEATURES else 'DISABLED'}")

# ============================================================================
# Page registration — core SCADA + Edge Monitor pages
# ============================================================================
from .scada_config import scada_enabled

if scada_enabled():
    from .pages import dashboard, edge_monitor, workflow, trend_enhanced_v2, alarms, communication
else:
    from .pages import (
    alarms,                  # /alarms
    alarms_hist_new,         # /alarms_hist_new
    alarms_hist_simple,      # /alarms_hist
    alarms_rt_new,           # /alarms_rt_new
    alarms_rt_simple,        # /alarms_rt (@rx.page in module)
    communication,           # /comm
    dashboard,               # / (@rx.page in module)
    edge_monitor,            # /edge-monitor (@rx.page in module)
    scada_alarm_comparison,  # /scada-alarm-comparison
    scada_alarm_viewer,      # /scada-alarms
    trend_enhanced_v2,       # /trend
    viewer_tag,              # /viewer-tag (@rx.page in module)
    workflow,                # /workflow (@rx.page in module)
)

# Optional AI / ML Forecasting pages - guarded by ENABLE_AI_FEATURES and try/except
if ENABLE_AI_FEATURES:
    try:
        from .pages import (
            forecast_player,     # /forecast
            model_performance,   # /model-performance
            training_wizard,     # /training-wizard
        )
        from .states.scheduler_state import SchedulerState  # noqa: F401
        logger.info("ML Forecasting pages (/forecast, /model-performance, /training-wizard) registered")
    except Exception as e:
        logger.warning(f"ML Forecasting pages skipped - failed to load dependencies: {e}")

    try:
        from .pages import ai_insights  # noqa: F401  /ai (@rx.page in module)
        logger.info("AI page /ai registered")
    except Exception as e:
        logger.warning(f"/ai page skipped - failed to load dependencies: {e}")
else:
    logger.info("AI/ML pages skipped - ENABLE_AI_FEATURES=false")
