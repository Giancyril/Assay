import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.database import check_db_health
from backend.app.routers.certificate import router as certificate_router
from backend.app.routers.checks import router as checks_router
from backend.app.routers.compare import router as compare_router
from backend.app.routers.documents import router as documents_router
from backend.app.routers.highlight import router as highlight_router
from backend.app.routers.indexing import router as indexing_router
from backend.app.routers.redline import router as redline_router
from backend.app.routers.reports import router as reports_router
from backend.app.routers.rules import router as rules_router
from backend.app.routers.stream import router as stream_router
from backend.app.routers.studio import router as studio_router

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
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
    lifespan=lifespan,
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
app.include_router(redline_router)
app.include_router(highlight_router)
app.include_router(stream_router)
app.include_router(studio_router)
app.include_router(certificate_router)
app.include_router(compare_router)
app.include_router(reports_router)


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
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/", include_in_schema=False)
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API. Visit /docs for OpenAPI documentation."}
