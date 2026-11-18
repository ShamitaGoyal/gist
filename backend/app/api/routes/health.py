"""Health and local LLM usage."""

import logging

from fastapi import APIRouter

from app.api.container import AppContainer
from app.api.dependencies import ContainerDep
from app.schemas.health import HealthResponse, LLMUsageResponse


logger = logging.getLogger("gist.api")
router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def health(container: ContainerDep):
    """Report whether the API and its local services are ready."""

    ready = _services_ready(container)
    provider = getattr(container.rag.llm_service, "provider_name", "ollama")
    return HealthResponse(
        status="healthy" if ready else "unavailable",
        llm_provider=provider,
        embedding_provider="ollama",
        embedding_model="nomic-embed-text",
        services_ready=ready,
    )


@router.get("/api/health/llm-usage", response_model=LLMUsageResponse)
def llm_usage(container: ContainerDep):
    """Return local Gemini counters. This does not call Gemini."""

    usage = container.rag.llm_service.get_gemini_usage()
    return LLMUsageResponse(**usage)


def _services_ready(container: AppContainer):
    try:
        container.registry.list_documents()
        container.vector_store.collection.count()
        return container.ingestion is not None and container.rag is not None
    except Exception:
        logger.exception("Health check could not reach a backend service")
        return False
