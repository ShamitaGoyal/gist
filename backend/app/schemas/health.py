"""Response shapes for health and local LLM usage."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Service status. Secrets are never included."""

    status: str = Field(description="healthy or unavailable.")
    llm_provider: str = Field(description="Answer provider: ollama or gemini.")
    embedding_provider: str = Field(description="Embedding provider. Always ollama.")
    embedding_model: str = Field(description="Embedding model. Always nomic-embed-text.")
    services_ready: bool = Field(description="Whether ingestion and retrieval services started.")


class LLMUsageResponse(BaseModel):
    """Local Gemini counters. This does not call Gemini."""

    total_attempted: int
    successful: int
    failed: int
    requests_last_minute: int
    requests_today: int
    daily_limit: int
    minute_limit: int
    remaining_daily_requests: int
