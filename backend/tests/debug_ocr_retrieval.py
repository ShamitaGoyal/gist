"""Find out why the OCR figure missed the hybrid top 3.

Uses the same question, PDF chunks, and in-memory Chroma setup as
test_ocr_hybrid_retrieval.py. Retrieval weights stay at 0.5 / 0.5.
The saved gist_documents collection is only read, not changed.

Run from the backend directory:

    python3 tests/debug_ocr_retrieval.py
"""

import sys
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_ocr_hybrid_retrieval as experiment


QUESTION = experiment.QUESTION
PREVIEW_CHARS = 400


def preview(text):
    compact = " ".join(text.split())
    if len(compact) <= PREVIEW_CHARS:
        return compact
    return compact[:PREVIEW_CHARS].rstrip() + "..."


def is_ocr(document):
    return document.metadata.get("source_type") == "ocr_figure"


def ocr_rank(documents):
    for rank, document in enumerate(documents, start=1):
        if is_ocr(document):
            return rank
    return None


def print_hits(documents, limit):
    for rank, document in enumerate(documents[:limit], start=1):
        print(f"\n--- Result {rank} ---")
        print(f"Source type: {document.metadata.get('source_type', 'unknown')}")
        print(f"Page number: {document.metadata.get('page_number', 'unknown')}")
        print("Content:")
        print(preview(document.page_content))


def prefix_snippets(pdf_documents):
    hits = []
    needle = "prefix"
    for document in pdf_documents:
        text = document.page_content
        folded = text.lower()
        start = folded.find(needle)
        if start < 0:
            continue
        left = max(0, start - 80)
        right = min(len(text), start + len(needle) + 80)
        hits.append(
            (
                document.metadata.get("page_number", "unknown"),
                " ".join(text[left:right].split()),
            )
        )
    return hits


def build_retrievers(corpus, embedding_service, candidate_k):
    """Same pieces as HybridSearchService, with a wider candidate list."""

    bm25_retriever = BM25Retriever.from_documents(corpus, k=candidate_k)
    vector_store = Chroma(
        client=chromadb.EphemeralClient(),
        collection_name="ocr_retrieval_debug",
        embedding_function=embedding_service.model,
    )
    vector_store.add_documents(corpus)
    semantic_retriever = vector_store.as_retriever(
        search_kwargs={"k": candidate_k}
    )
    hybrid_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, semantic_retriever],
        weights=[0.5, 0.5],
    )
    return bm25_retriever, vector_store, semantic_retriever, hybrid_retriever


def main():
    count_before = experiment.persistent_collection_count()

    print("Extracting and chunking the Meridian PDF...")
    pages = experiment.extract_pdf(str(experiment.PDF_PATH))
    pdf_chunks = experiment.chunk_pages(pages, document_id="meridian")
    markdown = experiment.OCR_PATH.read_text(encoding="utf-8")
    pdf_documents = [
        experiment.copy_for_experiment(chunk, "pdf_extraction")
        for chunk in pdf_chunks
    ]
    ocr_doc = experiment.ocr_document(markdown)
    corpus = pdf_documents + [ocr_doc]

    embedding_service = experiment.EmbeddingService()
    bm25_retriever, vector_store, semantic_retriever, hybrid_retriever = (
        build_retrievers(corpus, embedding_service, candidate_k=10)
    )

    print(f"\nQuestion: {QUESTION}")

    print("\n=== 1. CORPUS INCLUSION ===")
    bm25_ocr = sum(1 for document in bm25_retriever.docs if is_ocr(document))
    chroma_got = vector_store.get(where={"source_type": "ocr_figure"})
    chroma_ocr = len(chroma_got.get("ids", []))
    print(f"BM25 documents: {len(bm25_retriever.docs)}")
    print(f"BM25 OCR documents: {bm25_ocr}")
    print(f"Semantic documents: {vector_store._collection.count()}")
    print(f"Semantic OCR documents: {chroma_ocr}")

    print("\n=== 2. BM25 TOP 5 ===")
    bm25_retriever.k = len(bm25_retriever.docs)
    bm25_results = bm25_retriever.invoke(QUESTION)
    print_hits(bm25_results, limit=5)
    bm25_ocr_rank = ocr_rank(bm25_results)
    print(f"\nOCR rank in the full BM25 list: {bm25_ocr_rank or 'not found'}")
    bm25_retriever.k = 10

    print("\n=== 3. SEMANTIC TOP 5 ===")
    semantic_retriever.search_kwargs["k"] = vector_store._collection.count()
    semantic_results = semantic_retriever.invoke(QUESTION)
    print_hits(semantic_results, limit=5)
    semantic_ocr_rank = ocr_rank(semantic_results)
    print(f"\nOCR rank in the full semantic list: {semantic_ocr_rank or 'not found'}")
    semantic_retriever.search_kwargs["k"] = 10

    print("\n=== 4. HYBRID TOP 10 ===")
    hybrid_results = hybrid_retriever.invoke(QUESTION)
    for rank, document in enumerate(hybrid_results[:10], start=1):
        print(
            f"{rank:2}. {document.metadata.get('source_type', 'unknown'):<16} "
            f"page {document.metadata.get('page_number', 'unknown')}"
        )
    hybrid_ocr_rank = ocr_rank(hybrid_results)
    if hybrid_ocr_rank is None:
        print("The OCR document does not appear in the hybrid results.")
    else:
        print(f"The OCR document is hybrid result {hybrid_ocr_rank}.")

    print("\n=== 5. PDF CHUNKS CONTAINING 'prefix' ===")
    prefix_hits = prefix_snippets(pdf_documents)
    if not prefix_hits:
        print("No regular PDF chunk contains the word 'prefix'.")
    else:
        print(f"{len(prefix_hits)} PDF chunk(s) contain 'prefix':")
        for page_number, snippet in prefix_hits:
            print(f"- Page {page_number}: {snippet}")

    print("\n=== SUMMARY ===")
    if bm25_ocr != 1 or chroma_ocr != 1:
        print(
            "The OCR document is missing from a retriever corpus "
            f"(BM25 has {bm25_ocr}, semantic search has {chroma_ocr})."
        )
    else:
        print(
            "The OCR document is in both corpora. "
            f"BM25 ranks it {bm25_ocr_rank}. "
            f"Semantic search ranks it {semantic_ocr_rank}."
        )
        if hybrid_ocr_rank is None:
            print(
                "It does not appear in the hybrid list. Each retriever only "
                "contributes its top 10, and reciprocal rank fusion did not "
                "keep the OCR document."
            )
        elif hybrid_ocr_rank > 3:
            print(
                f"It is hybrid result {hybrid_ocr_rank}, so it is ranking "
                "below the top 3 rather than missing from the corpus."
            )
        else:
            print(f"It is inside the hybrid top 3, at rank {hybrid_ocr_rank}.")

    count_after = experiment.persistent_collection_count()
    print(f"Saved gist_documents count: {count_before} before, {count_after} after.")
    if count_before != count_after:
        raise RuntimeError("The persistent Chroma collection changed during the test.")


if __name__ == "__main__":
    main()
