"""Run semantic-only retrieval against hybrid retrieval on the Meridian PDF.

Usage, from the backend directory:

    python3 tests/run_retrieval_evaluation.py

The script extracts and chunks the PDF once, stores those chunks in Chroma,
asks both retrievers the same questions, and writes metrics, charts, and the
report under data/evaluation_results/. It does not call the LLM.
"""

import json
import os
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search import HybridSearchService
from app.services.pdf_service import extract_pdf
from app.services.retrieval_evaluator import (
    HYBRID,
    SEMANTIC,
    SENSITIVITY_THRESHOLDS,
    aggregate_metrics,
    chunk_id_from_metadata,
    load_stored_embeddings,
    page_number_from_metadata,
    rejection_rate_at_threshold,
    score_system,
    squared_l2,
    utc_timestamp,
    validate_questions,
    verify_distance_matches_chroma,
    write_outputs,
)
from app.services.semantic_chunker import chunk_pages
from app.services.vector_store import VectorStore


TOP_K = 3
MAX_DISTANCE = 0.75
LATENCY_REPETITIONS = 3
WARMUP_QUERY = "warmup"
DATASET_PATH = BACKEND_ROOT / "data" / "evaluation_questions.json"
PDF_PATH = BACKEND_ROOT / "data" / "pdf_files" / "meridian.pdf"
OUTPUT_DIR = BACKEND_ROOT / "data" / "evaluation_results"


def main():
    # Services store Chroma at the relative path data/chroma_db.
    os.chdir(BACKEND_ROOT)
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    questions = dataset["questions"]
    validate_questions(questions)

    print(f"Loading {PDF_PATH.name} and chunking it once...")
    pages = extract_pdf(str(PDF_PATH))
    chunks = chunk_pages(pages, document_id="meridian")
    if not chunks:
        raise RuntimeError("Semantic chunking produced no chunks")
    pages_present = sorted({int(chunk.metadata["page_number"]) for chunk in chunks})
    _require_expected_pages(questions, pages_present)
    print(f"Chunks: {len(chunks)}. Pages with text: {pages_present}")

    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    _replace_collection(vector_store, chunks, embedding_service)
    embeddings_by_id = load_stored_embeddings(vector_store.collection)
    verify_distance_matches_chroma(vector_store.collection, embeddings_by_id)

    print("Building hybrid search on the same chunks...")
    hybrid_search = HybridSearchService(chunks)
    _warmup(embedding_service, vector_store, hybrid_search)

    question_results = []
    for index, question in enumerate(questions, start=1):
        print(f"[{index}/{len(questions)}] {question['question_id']}")
        question_results.append(
            evaluate_question(
                question,
                embedding_service,
                vector_store,
                hybrid_search,
                embeddings_by_id,
            )
        )

    aggregate = aggregate_metrics(question_results)
    sensitivity = {
        f"{threshold:.2f}": rejection_rate_at_threshold(question_results, threshold)
        for threshold in SENSITIVITY_THRESHOLDS
    }
    results = {
        "timestamp": utc_timestamp(),
        "dataset_id": dataset["dataset_id"],
        "source_pdf": dataset["source_pdf"],
        "answerable_questions": sum(1 for item in questions if item["answerable"]),
        "unanswerable_questions": sum(
            1 for item in questions if not item["answerable"]
        ),
        "chunk_count": len(chunks),
        "pages_present": pages_present,
        "configuration": {
            "top_k": TOP_K,
            "max_distance": MAX_DISTANCE,
            "distance_metric": "squared L2, matching Chroma's default space",
            "embedding_model": "nomic-embed-text",
            "chroma_collection": "gist_documents",
            "hybrid_rrf_weights": list(hybrid_search.hybrid_retriever.weights),
            "hybrid_rrf_c": hybrid_search.hybrid_retriever.c,
            "hybrid_per_retriever_k": 3,
            "latency_repetitions": LATENCY_REPETITIONS,
            "warmup_query_excluded_from_metrics": WARMUP_QUERY,
            "llm_used": False,
            "hybrid_rejection": (
                "A hybrid chunk is accepted only when its squared L2 distance "
                f"to the query embedding is <= {MAX_DISTANCE}. "
                "This threshold is the existing VectorStore default. "
                "It is not applied to RRF scores, and it was not fit on this question set."
            ),
        },
        "aggregate_metrics": aggregate,
        "rejection_sensitivity": sensitivity,
        "questions": question_results,
    }

    json_path, report_path = write_outputs(results, OUTPUT_DIR)
    print_summary(aggregate, json_path, report_path)


def evaluate_question(
    question,
    embedding_service,
    vector_store,
    hybrid_search,
    embeddings_by_id,
):
    """Run both systems on one question and attach metric fields."""

    question_id = question["question_id"]
    semantic_payload, semantic_latency = retrieve_semantic(
        question, embedding_service, vector_store
    )
    query_embedding, semantic_retrieved = semantic_payload
    semantic_scored = build_semantic_result(
        question,
        vector_store,
        query_embedding,
        semantic_retrieved,
        semantic_latency,
    )

    hybrid_docs, hybrid_latency = retrieve_hybrid(question, hybrid_search)
    hybrid_scored = build_hybrid_result(
        question,
        hybrid_docs,
        query_embedding,
        embeddings_by_id,
        hybrid_latency,
    )

    return {
        "question_id": question_id,
        "question": question["question"],
        "answerable": question["answerable"],
        "question_type": question["question_type"],
        "expected_pages": question["expected_pages"],
        "notes": question.get("notes", ""),
        "systems": {
            SEMANTIC: semantic_scored,
            HYBRID: hybrid_scored,
        },
    }


def retrieve_semantic(question, embedding_service, vector_store):
    """Time query embedding plus VectorStore.search. Keep the first run's hits."""

    latencies = []
    first_result = None
    for attempt in range(LATENCY_REPETITIONS):
        try:
            started = time.perf_counter()
            query_embedding = embedding_service.embed_query(question["question"])
            retrieved = vector_store.search(
                query_embedding,
                top_k=TOP_K,
                max_distance=MAX_DISTANCE,
            )
            latencies.append(time.perf_counter() - started)
        except Exception as exc:
            raise RuntimeError(
                f"Retrieval failed for question {question['question_id']} "
                f"(semantic): {exc}"
            ) from exc
        if attempt == 0:
            first_result = (query_embedding, retrieved)
    return first_result, latencies


def retrieve_hybrid(question, hybrid_search):
    """Time HybridSearchService.search only. Keep the first run's ranking."""

    latencies = []
    first_docs = None
    for attempt in range(LATENCY_REPETITIONS):
        try:
            started = time.perf_counter()
            documents = hybrid_search.search(question["question"])
            latencies.append(time.perf_counter() - started)
        except Exception as exc:
            raise RuntimeError(
                f"Retrieval failed for question {question['question_id']} "
                f"(hybrid): {exc}"
            ) from exc
        if attempt == 0:
            first_docs = documents[:TOP_K]
    return first_docs, latencies


def build_semantic_result(
    question,
    vector_store,
    query_embedding,
    retrieved,
    latencies,
):
    """Split the raw top-k into accepted chunks and distance rejections."""

    question_id = question["question_id"]
    raw = vector_store.collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )
    expected_pages = set(question["expected_pages"])
    accepted = []
    rejected = []
    candidates = []

    raw_ids = raw["ids"][0] if raw["ids"] else []
    for rank, chunk_id in enumerate(raw_ids, start=1):
        metadata = raw["metadatas"][0][rank - 1]
        distance = float(raw["distances"][0][rank - 1])
        page_number = page_number_from_metadata(metadata, question_id, SEMANTIC)
        candidate = {
            "rank": rank,
            "chunk_id": chunk_id,
            "page_number": page_number,
            "distance": round(distance, 6),
            "relevant": page_number in expected_pages,
        }
        candidates.append(candidate)
        if distance <= MAX_DISTANCE:
            accepted.append({**candidate, "accepted": True})
        else:
            rejected.append(
                {
                    **candidate,
                    "accepted": False,
                    "reason": (
                        f"squared L2 distance {distance:.4f} exceeds "
                        f"max_distance {MAX_DISTANCE}"
                    ),
                }
            )

    search_ids = list(retrieved["ids"][0]) if retrieved["ids"] else []
    accepted_ids = [item["chunk_id"] for item in accepted]
    if search_ids != accepted_ids:
        raise RuntimeError(
            f"Semantic filter mismatch for {question_id}: "
            f"VectorStore.search returned {search_ids}, "
            f"distance gate returned {accepted_ids}"
        )

    scored = score_system(question, accepted, rejected, latencies)
    scored["distance_candidates"] = candidates
    return scored


def build_hybrid_result(
    question,
    documents,
    query_embedding,
    embeddings_by_id,
    latencies,
):
    """Score the RRF top-k, then accept chunks with the distance gate."""

    question_id = question["question_id"]
    expected_pages = set(question["expected_pages"])
    retrieved = []
    rejected = []
    candidates = []

    for rank, document in enumerate(documents, start=1):
        try:
            chunk_id = chunk_id_from_metadata(document.metadata, question_id, HYBRID)
            page_number = page_number_from_metadata(
                document.metadata, question_id, HYBRID
            )
        except KeyError as exc:
            raise RuntimeError(
                f"Retrieval failed for question {question_id} (hybrid): {exc}"
            ) from exc
        if chunk_id not in embeddings_by_id:
            raise RuntimeError(
                f"Retrieval failed for question {question_id} (hybrid): "
                f"chunk {chunk_id} is not in the Chroma collection"
            )
        distance = squared_l2(query_embedding, embeddings_by_id[chunk_id])
        relevant = page_number in expected_pages
        candidate = {
            "rank": rank,
            "chunk_id": chunk_id,
            "page_number": page_number,
            "distance": round(distance, 6),
            "relevant": relevant,
        }
        candidates.append(candidate)
        accepted = distance <= MAX_DISTANCE
        retrieved.append({**candidate, "accepted": accepted})
        if not accepted:
            rejected.append(
                {
                    **candidate,
                    "accepted": False,
                    "reason": (
                        f"squared L2 distance {distance:.4f} exceeds "
                        f"max_distance {MAX_DISTANCE}; "
                        "RRF rank was not used as a confidence score"
                    ),
                }
            )

    scored = score_system(question, retrieved, rejected, latencies)
    scored["distance_candidates"] = candidates
    return scored


def _replace_collection(vector_store, chunks, embedding_service):
    """Store this run's chunks so BM25 and Chroma search the same text."""

    texts = [chunk.page_content for chunk in chunks]
    print(f"Embedding {len(texts)} chunks for Chroma...")
    embeddings = embedding_service.embed_documents(texts)
    if len(embeddings) != len(chunks):
        raise RuntimeError(
            f"Embedding count {len(embeddings)} does not match chunk count {len(chunks)}"
        )

    existing_ids = list(vector_store.collection.get()["ids"])
    stored = vector_store.add_documents(chunks, embeddings)
    print(f"Upserted {stored} chunks into gist_documents")
    new_ids = {
        f"{chunk.metadata['document_id']}_{int(chunk.metadata['chunk_index'])}"
        for chunk in chunks
    }
    stale_ids = [chunk_id for chunk_id in existing_ids if chunk_id not in new_ids]
    if stale_ids:
        vector_store.collection.delete(ids=stale_ids)
        print(f"Removed {len(stale_ids)} stale chunks from the previous index")


def _require_expected_pages(questions, pages_present):
    present = set(pages_present)
    for question in questions:
        missing = [
            page for page in question["expected_pages"] if page not in present
        ]
        if missing:
            raise RuntimeError(
                f"{question['question_id']} expects pages {missing}, "
                f"but chunking produced no chunks for them. Pages present: {pages_present}"
            )


def _warmup(embedding_service, vector_store, hybrid_search):
    """Load the embedding model before timed questions."""

    print("Warming up both retrievers...")
    embedding = embedding_service.embed_query(WARMUP_QUERY)
    vector_store.search(embedding, top_k=TOP_K, max_distance=MAX_DISTANCE)
    hybrid_search.search(WARMUP_QUERY)


def print_summary(aggregate, json_path, report_path):
    print("\n=== RETRIEVAL EVALUATION ===")
    header = f"{'Metric':<28} {'Semantic':>12} {'Hybrid':>12}"
    print(header)
    rows = [
        ("Hit rate", "hit_rate", True),
        ("Precision@3", "precision_at_3", True),
        ("Recall@3", "recall_at_3", True),
        ("MRR", "mrr", True),
        ("Unanswerable rejection", "unanswerable_rejection_rate", True),
        ("Retrieval coverage", "retrieval_coverage", True),
        ("Average latency (s)", "average_latency_seconds", False),
    ]
    for label, key, as_percent in rows:
        semantic = aggregate["semantic"][key]
        hybrid = aggregate["hybrid"][key]
        if as_percent:
            print(f"{label:<28} {semantic:>11.1%} {hybrid:>11.1%}")
        else:
            print(f"{label:<28} {semantic:>11.3f} {hybrid:>11.3f}")
    print(f"\nResults: {json_path}")
    print(f"Report:  {report_path}")


if __name__ == "__main__":
    main()
