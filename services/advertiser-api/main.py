"""FastAPI Advertiser/DSP API application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from config import get_settings
from db.postgres import DatabaseManager
from services.redis_service import RedisService
from routers import auth, segments, targeting, reports

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()


# Global state
db_manager = None
redis_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown."""
    settings = get_settings()

    # Startup
    logger.info("Starting Advertiser API", version=settings.VERSION)

    global db_manager, redis_service
    db_manager = DatabaseManager(settings.DATABASE_URL)
    await db_manager.initialize()
    await db_manager.create_tables()

    redis_service = RedisService(settings.REDIS_URL)
    await redis_service.initialize()

    logger.info("Database and Redis connections initialized")

    yield

    # Shutdown
    logger.info("Shutting down Advertiser API")
    await db_manager.close()
    await redis_service.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Advertiser/DSP API",
        description="ACRaaS Advertiser API for DSP segment management and targeting",
        version=settings.VERSION,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Include routers
    app.include_router(auth.router)
    app.include_router(segments.router)
    app.include_router(targeting.router)
    app.include_router(reports.router)

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.error(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            "Unhandled exception",
            error=str(exc),
            path=str(request.url),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # Health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "advertiser-api",
            "version": settings.VERSION,
        }

    # Metrics endpoint placeholder
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return {"status": "metrics available at /metrics"}

    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        reload=False,
    )
