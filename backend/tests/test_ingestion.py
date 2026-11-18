"""Ingest the Meridian PDF into an in-memory Chroma collection.

The production gist_documents collection is only counted, not written.

Run from the backend directory:

    python3 tests/test_ingestion.py
"""

import sys
import tempfile
from pathlib import Path

import chromadb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.document_registry import DocumentRegistry
from app.services.ingestion_service import IngestionError, IngestionService
from app.services.vector_store import VectorStore


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = BACKEND_ROOT / "data" / "pdf_files" / "meridian.pdf"
CHROMA_PATH = BACKEND_ROOT / "data" / "chroma_db"
DOCUMENT_ID = "meridian"
EXPECTED_PAGES = 14


def production_count():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_collection("gist_documents").count()


def expect_error(service, pdf_path, document_id):
    try:
        service.ingest_document(pdf_path, document_id)
    except IngestionError as exc:
        print(f"Expected error: {exc}")
        return
    raise AssertionError(
        f"ingest_document({pdf_path!r}, {document_id!r}) should have failed"
    )


def main():
    count_before = production_count()
    isolated_store = VectorStore(
        client=chromadb.EphemeralClient(),
        collection_name="ingestion_test",
    )
    registry = DocumentRegistry(
        Path(tempfile.mkdtemp()) / "document_registry.json"
    )
    service = IngestionService(vector_store=isolated_store, registry=registry)

    expect_error(service, PDF_PATH.with_name("missing.pdf"), DOCUMENT_ID)
    expect_error(service, PDF_PATH, "  ")

    print(f"Ingesting {PDF_PATH.name} into an in-memory collection...")
    stats = service.ingest_document(str(PDF_PATH), DOCUMENT_ID)

    stored = isolated_store.collection.get(include=["metadatas", "embeddings"])
    stored_ids = set(stored["ids"])
    expected_ids = {
        f"{DOCUMENT_ID}_{index}" for index in range(stats["total_chunks"])
    }

    assert stats["document_id"] == DOCUMENT_ID
    assert stats["ingestion_status"] == "success"
    assert stats["total_pages"] == EXPECTED_PAGES
    assert stats["total_chunks"] > 0
    assert stats["total_embeddings"] == stats["total_chunks"]
    assert isolated_store.collection.count() == stats["total_chunks"]
    assert stored_ids == expected_ids
    assert all(
        metadata["document_id"] == DOCUMENT_ID for metadata in stored["metadatas"]
    )
    assert all(len(vector) > 0 for vector in stored["embeddings"])

    count_after = production_count()
    if count_before != count_after:
        raise AssertionError(
            "Production gist_documents changed: "
            f"{count_before} before, {count_after} after"
        )

    print("\n=== INGESTION TEST ===")
    print(f"document_id:      {stats['document_id']}")
    print(f"total_pages:      {stats['total_pages']}")
    print(f"total_chunks:     {stats['total_chunks']}")
    print(f"total_embeddings: {stats['total_embeddings']}")
    print(f"ingestion_status: {stats['ingestion_status']}")
    print(f"stored_ids:       {DOCUMENT_ID}_0 .. {DOCUMENT_ID}_{stats['total_chunks'] - 1}")
    print(f"embedding_size:   {len(stored['embeddings'][0])}")
    print(f"gist_documents:   {count_before} before, {count_after} after")
    print("Passed.")


if __name__ == "__main__":
    main()
