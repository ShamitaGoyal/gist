"""Re-ingestion and document-status tests on isolated storage.

Run from the backend directory:

    python3 tests/test_document_workflow.py
"""

import sys
import tempfile
from pathlib import Path

import chromadb
import pymupdf
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.document_registry import DocumentRegistry
from app.services.ingestion_service import IngestionError, IngestionService
from app.services.vector_store import VectorStore


BACKEND_ROOT = Path(__file__).resolve().parents[1]
CHROMA_PATH = BACKEND_ROOT / "data" / "chroma_db"


def production_count():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_collection("gist_documents").count()


def write_pdf(path, page_texts):
    document = pymupdf.open()
    for text in page_texts:
        page = document.new_page()
        page.insert_text((72, 72), text, fontsize=11)
    document.save(path)
    document.close()


def chunk(document_id, index, text):
    return Document(
        page_content=text,
        metadata={
            "document_id": document_id,
            "chunk_index": index,
            "page_number": index + 1,
            "section_headings": ["Test"],
            "source_type": "pdf_extraction",
        },
    )


def test_failed_replacement_restores_previous_chunks():
    store = VectorStore(
        client=chromadb.EphemeralClient(),
        collection_name="replacement_rollback",
    )
    original = [
        chunk("alpha", 0, "alpha original zero"),
        chunk("alpha", 1, "alpha original one"),
        chunk("alpha", 2, "alpha original two"),
    ]
    other = [chunk("beta", 0, "beta stays")]
    vectors = [[0.1, 0.2, 0.3]]
    store.add_documents(original, vectors * 3)
    store.add_documents(other, vectors)

    class FlakyStore(VectorStore):
        def __init__(self, wrapped):
            self.client = wrapped.client
            self.collection = wrapped.collection
            self.calls = 0

        def delete_ids(self, ids):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("delete failed")
            super().delete_ids(ids)

    flaky = FlakyStore(store)
    replacement = [chunk("alpha", 0, "alpha replacement")]
    try:
        flaky.replace_document(replacement, vectors)
    except RuntimeError as exc:
        print(f"Expected replacement error: {exc}")
    else:
        raise AssertionError("A failed delete should abort the replacement")

    alpha = {item.page_content for item in store.documents_for("alpha")}
    beta = {item.page_content for item in store.documents_for("beta")}
    assert alpha == {
        "alpha original zero",
        "alpha original one",
        "alpha original two",
    }
    assert beta == {"beta stays"}
    print("Rollback kept the previous alpha chunks and left beta untouched.")


def test_reingest_and_registry():
    count_before = production_count()
    directory = Path(tempfile.mkdtemp())
    first_pdf = directory / "alpha_v1.pdf"
    second_pdf = directory / "alpha_v2.pdf"
    other_pdf = directory / "beta.pdf"
    paragraph = (
        "Meridian describes overview detail interfaces through a declarative "
        "specification. This page is long enough to remain its own chunk. "
    )
    write_pdf(
        first_pdf,
        [paragraph + f" Version one page {number}." for number in (1, 2, 3)],
    )
    write_pdf(second_pdf, [paragraph + " Version two has only this page."])
    write_pdf(other_pdf, [paragraph + " UNIQUE_ZEBRA_TOKEN belongs to beta."])

    store = VectorStore(
        client=chromadb.EphemeralClient(),
        collection_name="workflow_test",
    )
    registry = DocumentRegistry(directory / "document_registry.json")
    service = IngestionService(
        vector_store=store,
        registry=registry,
        ocr_enabled=False,
    )

    try:
        service.ingest_document(str(directory / "missing.pdf"), "alpha")
    except IngestionError as exc:
        print(f"Expected missing-file error: {exc}")
    else:
        raise AssertionError("A missing PDF should fail ingestion")
    failed = registry.get_document("alpha")
    assert failed["ingestion_status"] == "failed"
    assert "PDF not found" in failed["error"]

    first = service.ingest_document(str(first_pdf), "alpha")
    other = service.ingest_document(str(other_pdf), "beta")
    assert first["total_chunks"] > other["total_chunks"]
    alpha_before = {item.metadata["chunk_index"] for item in store.documents_for("alpha")}
    beta_before = [item.page_content for item in store.documents_for("beta")]

    second = service.ingest_document(str(second_pdf), "alpha")
    assert second["total_chunks"] < first["total_chunks"]
    alpha_docs = store.documents_for("alpha")
    alpha_ids = {
        f"alpha_{int(item.metadata['chunk_index'])}" for item in alpha_docs
    }
    stored_alpha = store.collection.get(where={"document_id": "alpha"})
    assert set(stored_alpha["ids"]) == alpha_ids
    assert alpha_before - {int(item.metadata["chunk_index"]) for item in alpha_docs}
    assert [item.page_content for item in store.documents_for("beta")] == beta_before
    assert any("UNIQUE_ZEBRA_TOKEN" in text for text in beta_before)

    record = registry.get_document("alpha")
    assert record["ingestion_status"] == "success"
    assert record["error"] is None
    assert record["filename"] == "alpha_v2.pdf"
    assert record["total_pages"] == second["total_pages"]
    assert record["total_chunks"] == second["total_chunks"]
    assert record["total_embeddings"] == second["total_embeddings"]
    assert record["created_at"]
    assert record["last_ingestion_at"]
    listed = {item["document_id"] for item in registry.list_documents()}
    assert listed == {"alpha", "beta"}

    count_after = production_count()
    if count_before != count_after:
        raise AssertionError(
            f"Production collection changed: {count_before} to {count_after}"
        )
    print(
        f"Re-ingested alpha from {first['total_chunks']} chunks "
        f"to {second['total_chunks']} chunks."
    )
    print(f"Registry documents: {sorted(listed)}")
    print(f"gist_documents: {count_before} before, {count_after} after")


def main():
    test_failed_replacement_restores_previous_chunks()
    test_reingest_and_registry()
    print("Passed.")


if __name__ == "__main__":
    main()
