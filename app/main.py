"""
Main FastAPI application for HostForGuest.
"""

import os
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_db_and_tables, close_databases, health_check_databases
from app.middleware.tenant_isolation import TenantIsolationMiddleware
from app.middleware.rate_limiting import RateLimitingMiddleware

log_dir = os.path.dirname(settings.log_file)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    try:
        await create_db_and_tables()
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        if settings.environment != "development":
            raise

    try:
        from app.services.a2a.telegram_handler import register_telegram_webhook

        await register_telegram_webhook()
    except Exception as e:
        logger.warning("Telegram webhook registration skipped: %s", e)

    yield

    logger.info("Shutting down databases")
    await close_databases()


app = FastAPI(
    title=f"{settings.app_name} API",
    version=settings.app_version,
    description=(
        "AI-powered local guide platform for accommodation hosts and their guests. "
        "Built by Syntagent.\n\n"
        "## AI Services & API Keys\n"
        "This platform uses AI services (OpenAI, Google Gemini) for personalized "
        "recommendations, itinerary generation, vector search, and content creation.\n\n"
        "**For Hosts — two options:**\n"
        "1. **Use your own API keys** — Go to Host Settings > AI Configuration and add "
        "your OpenAI / Google AI keys. Your keys, your usage, full control over costs.\n"
        "2. **Use Syntagent-managed keys** — Contact us for a subscription plan. "
        "No API key setup needed, we handle the infrastructure.\n\n"
        "AI features (itinerary generation, guest recommendations, vector search) "
        "require at least one active API key to function.\n\n"
        "**Grace Period:** New hosts get 3 days of free AI access with Syntagent-managed "
        "keys — no setup needed. After the grace period, add your own keys or subscribe."
        "\n\n"
        "Note: Guests can always browse recommendations and local content "
        "without an API key — only AI-generated features (itineraries, smart search) "
        "require one."
    ),
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    docs_url=f"{settings.api_v1_str}/docs",
    redoc_url=f"{settings.api_v1_str}/redoc",
    lifespan=lifespan
)

is_dev = settings.is_development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if is_dev else settings.cors_origins_list,
    allow_credentials=not is_dev,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TenantIsolationMiddleware)
app.add_middleware(RateLimitingMiddleware, requests_per_minute=60, requests_per_hour=1000)


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "description": (
            "AI-powered local guide platform for accommodation hosts and their guests. "
            "Built by Syntagent."
        ),
        "version": settings.app_version,
        "status": "healthy",
        "environment": settings.environment,
        "focus_area": settings.default_location
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health/databases")
async def database_health_check():
    health_status = await health_check_databases()
    return {
        "databases": health_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


from app.api.v1.api import api_router
app.include_router(api_router, prefix=settings.api_v1_str)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
