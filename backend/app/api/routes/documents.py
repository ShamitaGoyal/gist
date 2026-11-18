"""Upload, list, inspect, and delete documents."""

import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.api.dependencies import ContainerDep
from app.api.errors import APIError, public_message
from app.schemas.document import (
    DeleteDocumentResponse,
    DocumentDetail,
    DocumentSummary,
)
from app.services.document_registry import DocumentNotFound
from app.services.ingestion_service import IngestionError


logger = logging.getLogger("gist.api")
router = APIRouter(prefix="/api/documents", tags=["documents"])
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


@router.post("/upload", response_model=DocumentDetail, status_code=201)
async def upload_document(container: ContainerDep, file: UploadFile = File(...)):
    """Save a PDF and ingest it with the existing ingestion service."""

    filename = _safe_pdf_name(file.filename)
    payload = await file.read()
    if not payload:
        raise APIError(400, "The uploaded file is empty.")
    if len(payload) > container.max_upload_bytes:
        raise APIError(413, "The uploaded file exceeds the size limit.")
    if not _looks_like_pdf(file.content_type, filename, payload):
        raise APIError(415, "Only PDF files can be uploaded.")

    document_id = uuid.uuid4().hex
    destination = _destination(container.upload_dir, document_id, filename)
    destination.write_bytes(payload)
    try:
        stats = container.ingestion.ingest_document(str(destination), document_id)
    except IngestionError:
        logger.exception("Ingestion failed for document %s", document_id)
        raise APIError(500, "Ingestion failed.") from None

    record = container.registry.get_document(document_id)
    return _detail(record, stats)


@router.get("", response_model=list[DocumentSummary])
def list_documents(container: ContainerDep):
    """List uploaded documents without storage paths."""

    return [_summary(record) for record in container.registry.list_documents()]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, container: ContainerDep):
    """Return one document's ingestion status."""

    return _detail(_require_record(container, document_id))


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
def delete_document(document_id: str, container: ContainerDep):
    """Remove one document's index, registry record, and uploaded PDF."""

    record = _require_record(container, document_id)
    try:
        container.vector_store.delete_document(document_id)
    except Exception:
        logger.exception("Could not delete index rows for %s", document_id)
        raise APIError(500, "Document deletion could not be completed.") from None
    try:
        _remove_upload(container.upload_dir, record.get("file_path"))
    except Exception:
        logger.exception("Could not delete the uploaded file for %s", document_id)
        raise APIError(500, "Document deletion could not be completed.") from None
    try:
        container.registry.remove_document(document_id)
    except Exception:
        logger.exception("Could not delete the registry record for %s", document_id)
        raise APIError(500, "Document deletion could not be completed.") from None
    return DeleteDocumentResponse(document_id=document_id)


def _require_record(container, document_id):
    try:
        return container.registry.get_document(document_id)
    except DocumentNotFound:
        raise APIError(404, "Document not found.") from None


def _summary(record):
    return DocumentSummary(
        document_id=record["document_id"],
        filename=record["filename"],
        ingestion_status=record["ingestion_status"],
        total_pages=record["total_pages"],
        total_chunks=record["total_chunks"],
        created_at=record["created_at"],
        last_ingestion_at=record["last_ingestion_at"],
    )


def _detail(record, stats=None):
    summary = _summary(record)
    embeddings = record["total_embeddings"]
    if stats is not None:
        embeddings = stats["total_embeddings"]
    return DocumentDetail(
        **summary.model_dump(),
        total_embeddings=embeddings,
        error=public_message(record.get("error")),
    )


def _safe_pdf_name(filename):
    base = Path(filename or "document.pdf").name
    stem = _SAFE_NAME.sub("_", Path(base).stem).strip("._")[:80]
    if not stem:
        stem = "document"
    return f"{stem}.pdf"


def _looks_like_pdf(content_type, filename, payload):
    if content_type not in (None, "", "application/pdf", "application/octet-stream"):
        return False
    if not filename.lower().endswith(".pdf"):
        return False
    return payload.startswith(b"%PDF")


def _destination(upload_dir, document_id, filename):
    folder = upload_dir / document_id
    folder.mkdir(parents=True, exist_ok=False)
    return folder / filename


def _remove_upload(upload_dir, file_path):
    if not file_path:
        return
    path = Path(file_path).resolve()
    root = upload_dir.resolve()
    if root != path and root not in path.parents:
        logger.error("Refusing to delete a file outside the upload directory")
        return
    path.unlink(missing_ok=True)
    parent = path.parent
    if parent != root:
        try:
            parent.rmdir()
        except OSError:
            logger.exception("Upload directory was not empty after file removal")
