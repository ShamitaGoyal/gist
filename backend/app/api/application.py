"""FastAPI application factory."""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.container import build_container
from app.api.errors import register_exception_handlers
from app.api.routes import documents, health, questions


logger = logging.getLogger("gist")


def create_app(container=None):
    """Build the API. Tests pass an isolated container instead of production storage."""

    application = FastAPI(
        title="Gist API",
        description=(
            "Upload a PDF, ingest it, and ask questions about that document. "
            "Answers use the indexed chunks for the requested document only."
        ),
        version="1.0.0",
    )
    application.state.container = container or build_container()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(documents.router)
    application.include_router(questions.router)

    @application.get("/", tags=["health"])
    def root():
        return {"message": "Gist API is running."}

    return application


def _allowed_origins():
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    origins = [
        origin.strip()
        for origin in raw.split(",")
        if origin.strip() and origin.strip() != "*"
    ]
    if not origins:
        logger.warning("CORS_ORIGINS was empty or wildcard. Using http://localhost:3000.")
        return ["http://localhost:3000"]
    return origins
