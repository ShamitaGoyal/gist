"""API tests against temporary storage and a fake answer model.

Run from the backend directory:

    python3 tests/test_api.py
"""

import sys
import tempfile
from pathlib import Path

import chromadb
import pymupdf
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.application import create_app
from app.api.container import build_container
from app.services.document_registry import DocumentRegistry
from app.services.ingestion_service import IngestionService
from app.services.rag_service import RAGService
from app.services.vector_store import VectorStore


BACKEND_ROOT = Path(__file__).resolve().parents[1]
CHROMA_PATH = BACKEND_ROOT / "data" / "chroma_db"
PDF_TEXT = "Meridian describes overview detail interfaces through a declarative specification."


class FakeLLM:
    provider_name = "ollama"

    def __init__(self):
        self.calls = 0

    def generate_answer(self, question, context):
        self.calls += 1
        return PDF_TEXT

    def get_gemini_usage(self):
        return {
            "total_attempted": 0,
            "successful": 0,
            "failed": 0,
            "requests_last_minute": 0,
            "requests_today": 0,
            "daily_limit": 50,
            "minute_limit": 5,
            "remaining_daily_requests": 50,
        }


def production_count():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_collection("gist_documents").count()


def write_pdf(path, text):
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    document.save(path)
    document.close()


def make_client(directory, max_upload_bytes):
    store = VectorStore(
        client=chromadb.EphemeralClient(),
        collection_name="api_test",
    )
    registry = DocumentRegistry(directory / "document_registry.json")
    llm = FakeLLM()
    ingestion = IngestionService(
        vector_store=store,
        registry=registry,
        ocr_enabled=False,
    )
    rag = RAGService(vector_store=store, registry=registry, llm_service=llm)
    container = build_container(
        registry=registry,
        vector_store=store,
        ingestion=ingestion,
        rag=rag,
        upload_dir=directory / "uploads",
        max_upload_bytes=max_upload_bytes,
        llm_service=llm,
    )
    return TestClient(create_app(container)), llm, store


def test_health_and_usage(client, llm):
    health = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert health.status_code == 200
    assert health.headers["access-control-allow-origin"] == "http://localhost:3000"
    body = health.json()
    assert body["status"] == "healthy"
    assert body["llm_provider"] == "ollama"
    assert body["embedding_provider"] == "ollama"
    assert body["embedding_model"] == "nomic-embed-text"
    assert body["services_ready"] is True
    assert "key" not in health.text.lower()

    before = llm.calls
    usage = client.get("/api/health/llm-usage")
    assert usage.status_code == 200
    assert usage.json()["total_attempted"] == 0
    assert llm.calls == before
    docs = client.get("/docs")
    redoc = client.get("/redoc")
    assert docs.status_code == 200
    assert redoc.status_code == 200
    print("Health, usage, and docs endpoints passed.")


def test_rejected_uploads(client):
    rejected = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert rejected.status_code == 415

    empty = client.post(
        "/api/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert empty.status_code == 400

    oversized = client.post(
        "/api/documents/upload",
        files={"file": ("big.pdf", b"%PDF" + b"x" * 80, "application/pdf")},
    )
    assert oversized.status_code == 413
    assert client.get("/api/documents").json() == []
    print("Invalid, empty, and oversized uploads were rejected.")


def test_rename_document(client):
    registry = client.app.state.container.registry
    registry.record_failure("alpha", "data/uploads/alpha/sample.pdf", "not ingested")
    renamed = client.patch("/api/documents/alpha", json={"filename": "Hotel specification"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["filename"] == "Hotel specification.pdf"
    assert registry.get_document("alpha")["file_path"].endswith("sample.pdf")
    blank = client.patch("/api/documents/alpha", json={"filename": "   "})
    assert blank.status_code == 400
    missing = client.patch("/api/documents/missing", json={"filename": "Other"})
    assert missing.status_code == 404
    print("Document rename passed.")


def test_library_questions_and_deletion(client, store):
    directory = Path(tempfile.mkdtemp())
    first_path = directory / "meridian-a.pdf"
    second_path = directory / "meridian-b.pdf"
    write_pdf(first_path, PDF_TEXT + " First copy.")
    write_pdf(second_path, PDF_TEXT + " Second copy stays.")

    def upload(path):
        with path.open("rb") as handle:
            response = client.post(
                "/api/documents/upload",
                files={"file": (path.name, handle, "application/pdf")},
            )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["ingestion_status"] == "success"
        assert body["total_pages"] == 1
        assert body["total_chunks"] > 0
        assert body["total_embeddings"] == body["total_chunks"]
        assert "file_path" not in body
        return body

    first = upload(first_path)
    second = upload(second_path)
    assert first["document_id"] != second["document_id"]
    assert first["filename"] == "meridian-a.pdf"

    listed = client.get("/api/documents")
    assert listed.status_code == 200
    assert {item["document_id"] for item in listed.json()} == {
        first["document_id"],
        second["document_id"],
    }

    detail = client.get(f"/api/documents/{first['document_id']}")
    assert detail.status_code == 200
    assert detail.json()["filename"] == "meridian-a.pdf"
    missing = client.get("/api/documents/does-not-exist")
    assert missing.status_code == 404

    pdf = client.get(f"/api/documents/{first['document_id']}/file")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")
    disposition = pdf.headers.get("content-disposition", "")
    assert "meridian-a.pdf" in disposition
    assert str(directory) not in disposition
    assert client.get("/api/documents/does-not-exist/file").status_code == 404

    blank = client.post(
        f"/api/documents/{first['document_id']}/ask",
        json={"question": "   "},
    )
    assert blank.status_code == 422
    unknown = client.post(
        "/api/documents/does-not-exist/ask",
        json={"question": "What does Meridian describe?"},
    )
    assert unknown.status_code == 404

    answer = client.post(
        f"/api/documents/{first['document_id']}/ask",
        json={"question": "What does Meridian describe?"},
    )
    assert answer.status_code == 200, answer.text
    payload = answer.json()
    assert payload["document_id"] == first["document_id"]
    assert payload["sources"]
    assert all(source["document_id"] == first["document_id"] for source in payload["sources"])
    assert all(source["chunk_id"].startswith(first["document_id"]) for source in payload["sources"])
    assert {source["source_type"] for source in payload["sources"]} <= {
        "pdf_extraction",
        "ocr_figure",
    }

    deleted = client.delete(f"/api/documents/{first['document_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert client.get(f"/api/documents/{first['document_id']}").status_code == 404
    assert client.get(f"/api/documents/{first['document_id']}/file").status_code == 404
    assert client.get(f"/api/documents/{second['document_id']}").status_code == 200
    assert store.documents_for(first["document_id"]) == []
    assert store.documents_for(second["document_id"])
    print("Upload, lookup, question, and isolated deletion passed.")


def main():
    count_before = production_count()
    with tempfile.TemporaryDirectory() as raw_directory:
        directory = Path(raw_directory)
        client, llm, store = make_client(directory, max_upload_bytes=50)
        test_health_and_usage(client, llm)
        test_rejected_uploads(client)
        test_rename_document(client)
        client.close()

        client, llm, store = make_client(directory, max_upload_bytes=2_000_000)
        test_library_questions_and_deletion(client, store)
        client.close()

    count_after = production_count()
    if count_before != count_after:
        raise AssertionError(
            f"Production collection changed: {count_before} to {count_after}"
        )
    print(f"gist_documents: {count_before} before, {count_after} after")
    print("Passed.")


if __name__ == "__main__":
    main()
