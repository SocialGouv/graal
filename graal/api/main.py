"""
FastAPI main application for GRAAL web interface.
"""

import logging
import logging.config
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graal.api.routes import authorization, database_builder, proconnect, users
from graal.api.routes.health import router as health_router
from graal.api.routes.processing import router as processing_router
from graal.api.services.database_builder_service import DatabaseBuilderService
from graal.api.services.job_registry import InMemoryJobRegistry
from graal.api.services.web_processing_service import WebProcessingService

logging.config.fileConfig("logging.conf")


# Global services
job_registry = InMemoryJobRegistry()
web_processing_service = WebProcessingService(job_registry=job_registry)
database_builder_service = DatabaseBuilderService(job_registry=job_registry)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan event handler."""
    # Startup
    logging.info("GRAAL Web API starting up...")
    yield
    # Shutdown
    logging.info("GRAAL Web API shutting down...")


# Create FastAPI application
app = FastAPI(
    title="GRAAL Web API",
    description="Web API for GRAAL (Gestion et Répartition Automatisée des Amendements Législatifs)",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS origins
cors_origins = ["http://localhost:5173"]  # Always allow local development

# Add production frontend URL if provided
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    cors_origins.append(frontend_url)

logging.info(f"CORS origins configured: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(processing_router, prefix="/api/v1")
app.include_router(database_builder.router, prefix="/api/v1")
app.include_router(authorization.router, prefix="/api/v1")
app.include_router(proconnect.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000, reload=True)
