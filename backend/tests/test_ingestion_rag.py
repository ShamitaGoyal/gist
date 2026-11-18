"""Ingest Meridian into isolated storage, then ask a document-specific question.

Run from the backend directory:

    python3 tests/test_ingestion_rag.py
"""

import sys
import tempfile
from pathlib import Path

import chromadb
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.document_registry import DocumentRegistry
from app.services.hybrid_search import HybridSearchService
from app.services.ingestion_service import IngestionService
from app.services.rag_service import RAGService
from app.services.vector_store import VectorStore


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = BACKEND_ROOT / "data" / "pdf_files" / "meridian.pdf"
CHROMA_PATH = BACKEND_ROOT / "data" / "chroma_db"
FIGURE_QUESTION = (
    "What does the dotted prefix in Meridian's data-binding specification indicate?"
)


def production_count():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_collection("gist_documents").count()


def write_other_pdf(path):
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "This separate paper is about UNIQUE_ZEBRA_TOKEN and nothing in Meridian.",
        fontsize=12,
    )
    document.save(path)
    document.close()


def main():
    count_before = production_count()
    directory = Path(tempfile.mkdtemp())
    other_pdf = directory / "other.pdf"
    write_other_pdf(other_pdf)

    store = VectorStore(
        client=chromadb.EphemeralClient(),
        collection_name="ingestion_rag_test",
    )
    registry = DocumentRegistry(directory / "document_registry.json")
    ingestion = IngestionService(vector_store=store, registry=registry)
    rag = RAGService(vector_store=store, registry=registry)

    try:
        rag.answer_document("What is Meridian?", "meridian")
    except ValueError as exc:
        print(f"Expected missing-document error: {exc}")
    else:
        raise AssertionError("A question before ingestion should fail")

    print("Ingesting the other document...")
    ingestion.ingest_document(str(other_pdf), "other_paper")
    print("Ingesting meridian.pdf...")
    stats = ingestion.ingest_document(str(PDF_PATH), "meridian")
    assert stats["total_pages"] == 14
    assert stats["total_chunks"] == stats["total_embeddings"]
    assert stats["ingestion_status"] == "success"

    documents = store.documents_for("meridian")
    pdf_chunks = [
        item for item in documents if item.metadata.get("source_type") == "pdf_extraction"
    ]
    ocr_chunks = [
        item for item in documents if item.metadata.get("source_type") == "ocr_figure"
    ]
    assert pdf_chunks
    assert ocr_chunks
    page4 = [item for item in ocr_chunks if int(item.metadata["page_number"]) == 4]
    assert page4, "Page 4 did not produce supplementary OCR content"
    assert "prefix" in page4[0].page_content.lower()

    print("Asking a Meridian question...")
    result = rag.answer_document(
        "How does Meridian support end-user customization?",
        "meridian",
    )
    assert result["answer"].strip()
    assert result["sources"]
    assert "Sources:" in result["answer"]
    for source in result["sources"]:
        assert source["document_id"] == "meridian"
        assert source["page_number"] is not None
        assert source["chunk_id"].startswith("meridian_")
        assert "UNIQUE_ZEBRA_TOKEN" not in source["chunk_id"]

    other_result = rag.answer_document(
        "What does UNIQUE_ZEBRA_TOKEN describe?",
        "other_paper",
    )
    assert other_result["sources"]
    assert {source["document_id"] for source in other_result["sources"]} == {
        "other_paper"
    }

    hybrid = HybridSearchService(
        documents,
        document_id="meridian",
        chroma_client=store.client,
        collection_name=store.collection.name,
    )
    figure_hits = hybrid.search(FIGURE_QUESTION)
    figure_types = [item.metadata.get("source_type") for item in figure_hits]
    prefix_hits = hybrid.search("Reference values from data with the prefix")
    prefix_types = [item.metadata.get("source_type") for item in prefix_hits]
    assert all(item.metadata.get("document_id") == "meridian" for item in figure_hits)
    assert "ocr_figure" in prefix_types

    count_after = production_count()
    if count_before != count_after:
        raise AssertionError(
            f"Production collection changed: {count_before} to {count_after}"
        )

    print("\n=== INGESTION TO RAG ===")
    print(f"pages: {stats['total_pages']}")
    print(f"pdf_chunks: {len(pdf_chunks)}")
    print(f"ocr_chunks: {len(ocr_chunks)} on pages "
          f"{sorted({int(item.metadata['page_number']) for item in ocr_chunks})}")
    print(f"answer_sources: {[(item['chunk_id'], item['page_number']) for item in result['sources']]}")
    print(f"figure_question_types: {figure_types}")
    print(f"prefix_sentence_types: {prefix_types}")
    print("Answer:")
    print(result["answer"])
    print(f"gist_documents: {count_before} before, {count_after} after")
    print("Passed.")


if __name__ == "__main__":
    main()
