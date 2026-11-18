"""Wires the existing services for one API process."""

import os
from dataclasses import dataclass
from pathlib import Path

from app.services.document_registry import DocumentRegistry
from app.services.ingestion_service import IngestionService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.vector_store import VectorStore


DEFAULT_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@dataclass
class AppContainer:
    """Services and upload settings shared by the routes."""

    registry: DocumentRegistry
    vector_store: VectorStore
    ingestion: IngestionService
    rag: RAGService
    upload_dir: Path
    max_upload_bytes: int


def build_container(
    registry=None,
    vector_store=None,
    ingestion=None,
    rag=None,
    upload_dir=None,
    max_upload_bytes=None,
    llm_service=None,
):
    """Create the default services, or accept isolated ones from tests."""

    store = vector_store or VectorStore()
    documents = registry or DocumentRegistry("data/document_registry.json")
    ingestion_service = ingestion or IngestionService(
        vector_store=store,
        registry=documents,
    )
    answer_service = rag or RAGService(
        vector_store=store,
        registry=documents,
        llm_service=llm_service,
    )
    directory = Path(upload_dir or os.getenv("GIST_UPLOAD_DIR", "data/uploads"))
    directory.mkdir(parents=True, exist_ok=True)
    limit = max_upload_bytes
    if limit is None:
        raw = os.getenv("GIST_MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES))
        limit = int(raw)
    return AppContainer(
        registry=documents,
        vector_store=store,
        ingestion=ingestion_service,
        rag=answer_service,
        upload_dir=directory,
        max_upload_bytes=limit,
    )
