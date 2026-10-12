import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database import check_db_health
from backend.app.routers.documents import router as documents_router
from backend.app.routers.indexing import router as indexing_router
from backend.app.routers.rules import router as rules_router
from backend.app.routers.checks import router as checks_router

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("compliance_agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Compliance Agent API: Contract & Policy Clause Verification and Rule Engine",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(documents_router)
app.include_router(indexing_router)
app.include_router(rules_router)
app.include_router(checks_router)


@app.get("/api/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """Health check endpoint reporting service status, database connectivity, and timestamp."""
    db_connected = await check_db_health()
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database_connected": db_connected,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API. Visit /docs for OpenAPI documentation."
    }
