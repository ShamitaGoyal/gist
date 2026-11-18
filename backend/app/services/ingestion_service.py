"""Coordinate PDF extraction, chunking, embedding, and indexing.

OCR figure text is added only when the normal page text does not already
contain that line. Chunk ids stay `{document_id}_{chunk_index}`.
"""

from pathlib import Path

from app.services.document_registry import DocumentRegistry
from app.services.embedding_service import EmbeddingService
from app.services.figure_ocr import supplement_figures
from app.services.pdf_service import extract_pdf
from app.services.semantic_chunker import chunk_pages
from app.services.vector_store import VectorStore


class IngestionError(Exception):
    """A document could not be extracted, embedded, or indexed."""


class IngestionService:
    def __init__(
        self,
        embedding_service=None,
        vector_store=None,
        registry=None,
        ocr_enabled=True,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.registry = registry or DocumentRegistry("data/document_registry.json")
        self.ocr_enabled = ocr_enabled

    def ingest_document(self, pdf_path, document_id):
        """Index one PDF and replace that document's previous chunks.

        Extraction, chunking, OCR, and embedding finish before any indexed
        row for the document is replaced. A failed replacement restores the
        previous rows. Chunks for other documents are left in place.
        """

        document_id = _require_document_id(document_id)
        try:
            return self._ingest(pdf_path, document_id)
        except IngestionError as exc:
            self.registry.record_failure(document_id, pdf_path, exc)
            raise

    def _ingest(self, pdf_path, document_id):
        pdf_path = _require_pdf(pdf_path)
        pages = _extract_pages(pdf_path)
        chunks = _chunk_pages(pages, document_id, pdf_path)
        for chunk in chunks:
            chunk.metadata["source_type"] = "pdf_extraction"
        if self.ocr_enabled:
            chunks.extend(_figure_chunks(pdf_path, pages, document_id))
        _assign_chunk_indexes(chunks, document_id)
        embeddings = _embed_chunks(self.embedding_service, chunks, document_id)
        try:
            self.vector_store.replace_document(chunks, embeddings)
        except Exception as exc:
            raise IngestionError(
                f"Indexing failed for {document_id}: {exc}"
            ) from exc

        self.registry.record_success(
            document_id,
            pdf_path,
            pages=len(pages),
            chunks=len(chunks),
            embeddings=len(embeddings),
        )
        return {
            "document_id": document_id,
            "total_pages": len(pages),
            "total_chunks": len(chunks),
            "total_embeddings": len(embeddings),
            "ingestion_status": "success",
        }


def _require_document_id(document_id):
    if not isinstance(document_id, str) or not document_id.strip():
        raise IngestionError("document_id is required")
    if document_id != document_id.strip():
        raise IngestionError("document_id cannot contain surrounding whitespace")
    return document_id


def _require_pdf(pdf_path):
    path = Path(pdf_path)
    if not path.is_file():
        raise IngestionError(f"PDF not found: {pdf_path}")
    return str(path)


def _extract_pages(pdf_path):
    try:
        pages = extract_pdf(pdf_path)
    except Exception as exc:
        raise IngestionError(f"PDF extraction failed for {pdf_path}: {exc}") from exc
    if not pages:
        raise IngestionError(f"PDF extraction returned no pages for {pdf_path}")
    return pages


def _chunk_pages(pages, document_id, pdf_path):
    try:
        chunks = chunk_pages(pages, document_id=document_id)
    except Exception as exc:
        raise IngestionError(
            f"Semantic chunking failed for {document_id}: {exc}"
        ) from exc
    if not chunks:
        raise IngestionError(f"Semantic chunking produced no chunks for {pdf_path}")
    for chunk in chunks:
        if chunk.metadata.get("document_id") != document_id:
            raise IngestionError(
                f"Chunk document_id {chunk.metadata.get('document_id')!r} "
                f"does not match {document_id!r}"
            )
    return chunks


def _figure_chunks(pdf_path, pages, document_id):
    try:
        return supplement_figures(pdf_path, pages, document_id)
    except Exception as exc:
        raise IngestionError(
            f"Figure OCR failed for {document_id}: {exc}"
        ) from exc


def _assign_chunk_indexes(chunks, document_id):
    for index, chunk in enumerate(chunks):
        chunk.metadata["document_id"] = document_id
        chunk.metadata["chunk_index"] = index
    indexes = [chunk.metadata["chunk_index"] for chunk in chunks]
    if indexes != list(range(len(chunks))):
        raise IngestionError(
            f"Chunk indexes for {document_id} are not consecutive: {indexes}"
        )


def _embed_chunks(embedding_service, chunks, document_id):
    texts = [chunk.page_content for chunk in chunks]
    try:
        embeddings = embedding_service.embed_documents(texts)
    except Exception as exc:
        raise IngestionError(f"Embedding failed for {document_id}: {exc}") from exc
    if len(embeddings) != len(chunks):
        raise IngestionError(
            f"Embedding count {len(embeddings)} does not match "
            f"chunk count {len(chunks)} for {document_id}"
        )
    return embeddings
