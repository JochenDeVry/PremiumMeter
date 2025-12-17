"""
FastAPI application initialization.
Configures CORS, error handling, logging, and API routes.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from src.config import settings
import logging
import sys

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Options Premium Analyzer API",
    description="API for querying historical options premium data, managing stock watchlists, and configuring data scraping schedules",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with detailed messages"""
    errors = exc.errors()
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "invalid_parameters",
            "message": "Request validation failed",
            "details": errors
        }
    )

# Global exception handler for uncaught exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred"
        }
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring.
    Returns 200 OK if service is running.
    """
    return {
        "status": "healthy",
        "service": "Options Premium Analyzer API",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "message": "Options Premium Analyzer API",
        "docs": "/docs",
        "health": "/health"
    }

# TODO: Import and include routers as endpoints are implemented
# from src.api.endpoints import query, watchlist, scheduler, stocks
# app.include_router(query.router, prefix="/api/query", tags=["Query"])
# app.include_router(watchlist.router, prefix="/api/watchlist", tags=["Watchlist"])
# app.include_router(scheduler.router, prefix="/api/scheduler", tags=["Scheduler"])
# app.include_router(stocks.router, prefix="/api/stocks", tags=["Stocks"])

# Startup event - initialize scheduler
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    logger.info("Starting Options Premium Analyzer API...")
    # TODO: Initialize APScheduler and load scraper configuration (Phase 3, T034)
    logger.info("API startup complete")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down Options Premium Analyzer API...")
    # TODO: Shutdown scheduler gracefully (Phase 3)
    logger.info("API shutdown complete")
