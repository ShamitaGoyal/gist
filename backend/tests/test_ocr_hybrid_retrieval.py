"""See whether an OCR figure page changes hybrid retrieval for one question.

The production HybridSearchService is wired to data/chroma_db. This test
builds the same BM25 + Chroma + RRF search on an in-memory collection so
the saved gist_documents collection is not changed.

Run from the backend directory:

    python3 tests/test_ocr_hybrid_retrieval.py
"""

import sys
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import extract_pdf
from app.services.semantic_chunker import chunk_pages


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = BACKEND_ROOT / "data" / "pdf_files" / "meridian.pdf"
OCR_PATH = BACKEND_ROOT / "data" / "evaluation_results" / "page4_structured.md"
CHROMA_PATH = BACKEND_ROOT / "data" / "chroma_db"

QUESTION = (
    "What does the dotted prefix in Meridian's data-binding specification indicate?"
)
TOP_K = 3
PREVIEW_CHARS = 700


def persistent_collection_count():
    """Read the saved collection. This does not add or delete anything."""

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_collection("gist_documents").count()


def copy_for_experiment(document, source_type):
    """Copy a chunk and mark where it came from.

    Chroma metadata cannot store lists, so section headings are joined.
    The original chunk objects are left unchanged.
    """

    metadata = {"source_type": source_type}
    for key, value in document.metadata.items():
        if isinstance(value, list):
            metadata[key] = " | ".join(str(part) for part in value)
        elif value is not None:
            metadata[key] = value
    return Document(page_content=document.page_content, metadata=metadata)


def ocr_document(markdown):
    return Document(
        page_content=markdown,
        metadata={
            "document_id": "meridian",
            "page_number": 4,
            "source_type": "ocr_figure",
        },
    )


def build_isolated_hybrid_search(documents, embedding_service):
    """Same retriever setup as HybridSearchService, on an ephemeral Chroma."""

    bm25_retriever = BM25Retriever.from_documents(documents, k=TOP_K)

    vector_store = Chroma(
        client=chromadb.EphemeralClient(),
        collection_name="ocr_hybrid_experiment",
        embedding_function=embedding_service.model,
    )
    vector_store.add_documents(documents)

    semantic_retriever = vector_store.as_retriever(search_kwargs={"k": TOP_K})
    hybrid_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, semantic_retriever],
        weights=[0.5, 0.5],
    )
    return hybrid_retriever


def preview(text):
    compact = text.strip()
    if len(compact) <= PREVIEW_CHARS:
        return compact
    return compact[:PREVIEW_CHARS].rstrip() + "..."


def main():
    count_before = persistent_collection_count()

    print("Extracting and chunking the Meridian PDF...")
    pages = extract_pdf(str(PDF_PATH))
    pdf_chunks = chunk_pages(pages, document_id="meridian")

    markdown = OCR_PATH.read_text(encoding="utf-8")
    corpus = [
        copy_for_experiment(chunk, "pdf_extraction")
        for chunk in pdf_chunks
    ]
    corpus.append(ocr_document(markdown))

    print(
        f"Corpus: {len(pdf_chunks)} PDF chunks + 1 OCR figure document "
        f"(in memory only)."
    )

    embedding_service = EmbeddingService()
    hybrid_retriever = build_isolated_hybrid_search(corpus, embedding_service)
    results = hybrid_retriever.invoke(QUESTION)[:TOP_K]

    print(f"\nQuestion: {QUESTION}")
    print(f"\n=== TOP {TOP_K} HYBRID RESULTS ===")

    ocr_rank = None
    for rank, document in enumerate(results, start=1):
        source_type = document.metadata.get("source_type", "unknown")
        page_number = document.metadata.get("page_number", "unknown")
        if source_type == "ocr_figure":
            ocr_rank = rank
        print(f"\n--- Result {rank} ---")
        print(f"Source type: {source_type}")
        print(f"Page number: {page_number}")
        print("Content:")
        print(preview(document.page_content))

    print("\n=== COMPARISON ===")
    if ocr_rank is None:
        print("The OCR-derived figure content is not in the top 3.")
    else:
        print(f"The OCR-derived figure content is result {ocr_rank} of the top 3.")

    count_after = persistent_collection_count()
    print(
        f"\nSaved gist_documents count: {count_before} before, {count_after} after."
    )
    if count_before != count_after:
        raise RuntimeError("The persistent Chroma collection changed during the test.")


if __name__ == "__main__":
    main()
