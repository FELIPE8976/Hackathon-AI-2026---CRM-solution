"""
Entry point for the CRM Multi-Agent API.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager

# asyncpg is incompatible with ProactorEventLoop (Windows default in Python 3.8+).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings

# ---------------------------------------------------------------------------
# Logging configuration — applied once at module load
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Silence noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

from app.core.limiter import limiter  # noqa: E402

# ---------------------------------------------------------------------------
# Lifespan: runs once on startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Pre-warm the DB connection pool so the first user request is not slow.
    # The cold TCP handshake through Docker can take ~20 s on Windows — paying
    # that cost once at startup is far better than on a live request.
    from app.core.database import engine
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection pool warmed up.")
    except Exception as exc:
        logger.warning("Could not pre-warm DB pool: %s", exc)

    yield

    await engine.dispose()
    logger.info("Database engine disposed. Shutdown complete.")


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

from app.api.endpoints import auth, metrics, supervisor, webhooks  # noqa: E402

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Multi-agent CRM automation system powered by LangGraph. "
        "Analyzes incoming client messages, evaluates SLAs and sentiment, "
        "and executes actions autonomously — with Human-in-the-Loop supervision "
        "for high-risk cases."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Attach limiter state and rate limit exceeded handler
# ---------------------------------------------------------------------------

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    detail = str(exc) if settings.DEBUG else "An unexpected error occurred. Please try again later."
    return JSONResponse(
        status_code=500,
        content={"detail": detail},
    )


# ---------------------------------------------------------------------------
# Middleware — order matters: request logging wraps everything
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d  (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Auth"],
)

app.include_router(
    webhooks.router,
    prefix="/api/v1/webhook",
    tags=["Webhook — Message Ingestion"],
)

app.include_router(
    supervisor.router,
    prefix="/api/v1/supervisor",
    tags=["Supervisor — Human-in-the-Loop"],
)

app.include_router(
    metrics.router,
    prefix="/api/v1/metrics",
    tags=["Metrics — Statistics Dashboard"],
)

# ---------------------------------------------------------------------------
# Health / root endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"], summary="Root")
async def root() -> dict:
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"], summary="Health check")
async def health_check() -> dict:
    return {"status": "healthy"}


@app.get("/health/db", tags=["Health"], summary="Database connectivity check")
async def health_db() -> dict:
    import traceback
    from sqlalchemy import text
    from app.core.database import engine
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.scalar()
        return {"status": "ok", "result": row}
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
