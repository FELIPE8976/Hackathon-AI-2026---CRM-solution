"""
Entry point for the CRM Multi-Agent API.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI

from app.core.config import settings
from app.api.endpoints import webhooks, supervisor

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

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
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

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
