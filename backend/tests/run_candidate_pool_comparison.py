"""Compare hybrid candidate pool sizes on the labeled Meridian questions.

Baseline asks BM25 and semantic search for 3 chunks each. The expanded run
asks each for 10. Both still keep the fused top 3, the 0.5/0.5 RRF weights,
and the existing squared-L2 acceptance gate.

The page 4 structured OCR document is added to both runs. Vectors live in an
in-memory Chroma collection. The saved gist_documents collection is only read
so this script can confirm it did not change.

Run from the backend directory:

    python3 tests/run_candidate_pool_comparison.py
"""

import json
import sys
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import extract_pdf
from app.services.retrieval_evaluator import (
    mean,
    precision_at_3,
    recall_at_3,
    reciprocal_rank,
    squared_l2,
    utc_timestamp,
    validate_questions,
)
from app.services.semantic_chunker import chunk_pages
from test_ocr_hybrid_retrieval import (
    OCR_PATH,
    PDF_PATH,
    copy_for_experiment,
    ocr_document,
    persistent_collection_count,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = BACKEND_ROOT / "data" / "evaluation_questions.json"
OUTPUT_DIR = BACKEND_ROOT / "data" / "evaluation_results"
JSON_PATH = OUTPUT_DIR / "candidate_pool_comparison.json"
REPORT_PATH = OUTPUT_DIR / "candidate_pool_comparison.md"

FINAL_K = 3
BASELINE_CANDIDATE_K = 3
EXPANDED_CANDIDATE_K = 10
MAX_DISTANCE = 0.75
WEIGHTS = [0.5, 0.5]
COLLECTION_NAME = "candidate_pool_experiment"
CONFIGS = (
    ("baseline", BASELINE_CANDIDATE_K),
    ("expanded", EXPANDED_CANDIDATE_K),
)


def build_corpus():
    """Chunk the PDF once and append the same OCR figure document."""

    pages = extract_pdf(str(PDF_PATH))
    pdf_chunks = chunk_pages(pages, document_id="meridian")
    if not pdf_chunks:
        raise RuntimeError("Semantic chunking produced no chunks")

    corpus = [
        copy_for_experiment(chunk, "pdf_extraction")
        for chunk in pdf_chunks
    ]
    ocr = ocr_document(OCR_PATH.read_text(encoding="utf-8"))
    used_indexes = {int(chunk.metadata["chunk_index"]) for chunk in pdf_chunks}
    ocr.metadata["chunk_index"] = max(used_indexes) + 1
    corpus.append(ocr)

    for document in corpus:
        document.metadata["experiment_id"] = (
            f"{document.metadata['document_id']}_"
            f"{int(document.metadata['chunk_index'])}"
        )
    return pdf_chunks, corpus


def require_expected_pages(questions, pdf_chunks):
    present = {int(chunk.metadata["page_number"]) for chunk in pdf_chunks}
    for question in questions:
        missing = [
            page for page in question["expected_pages"] if page not in present
        ]
        if missing:
            raise RuntimeError(
                f"{question['question_id']} expects pages {missing}, "
                f"but chunking produced no PDF chunks for them"
            )


def build_retrievers(corpus, embedding_service):
    """One BM25 index and one ephemeral Chroma index, shared by both runs."""

    bm25_retriever = BM25Retriever.from_documents(
        corpus,
        k=BASELINE_CANDIDATE_K,
    )
    vector_store = Chroma(
        client=chromadb.EphemeralClient(),
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_service.model,
    )
    vector_store.add_documents(corpus)
    semantic_retriever = vector_store.as_retriever(
        search_kwargs={"k": BASELINE_CANDIDATE_K}
    )
    hybrid_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, semantic_retriever],
        weights=WEIGHTS,
    )
    return bm25_retriever, semantic_retriever, hybrid_retriever, vector_store


def load_embeddings(vector_store, corpus):
    """Read the vectors Chroma stored, keyed by experiment_id."""

    stored = vector_store.get(include=["embeddings", "metadatas"])
    embeddings = {}
    for metadata, vector in zip(stored["metadatas"], stored["embeddings"]):
        experiment_id = metadata["experiment_id"]
        embeddings[experiment_id] = [float(value) for value in vector]

    expected_ids = {document.metadata["experiment_id"] for document in corpus}
    if set(embeddings) != expected_ids:
        raise RuntimeError(
            "Ephemeral collection ids do not match the shared corpus"
        )
    ocr_ids = [
        document.metadata["experiment_id"]
        for document in corpus
        if document.metadata["source_type"] == "ocr_figure"
    ]
    if len(ocr_ids) != 1 or ocr_ids[0] not in embeddings:
        raise RuntimeError("The OCR document is missing from the vector corpus")
    return embeddings


def search(query, candidate_k, bm25_retriever, semantic_retriever, hybrid_retriever):
    """Fuse the two retrievers and keep the top 3. Weights stay 0.5/0.5."""

    bm25_retriever.k = candidate_k
    semantic_retriever.search_kwargs["k"] = candidate_k
    return hybrid_retriever.invoke(query)[:FINAL_K]


def score_results(question, documents, query_embedding, embeddings_by_id):
    """Score one fused top-3 list with the existing metric functions."""

    expected_pages = set(question["expected_pages"])
    retrieved = []
    for rank, document in enumerate(documents, start=1):
        metadata = document.metadata
        experiment_id = metadata.get("experiment_id")
        if experiment_id not in embeddings_by_id:
            raise RuntimeError(
                f"{question['question_id']} retrieved {experiment_id}, "
                "which is not in the shared corpus"
            )
        page_number = int(metadata["page_number"])
        distance = squared_l2(query_embedding, embeddings_by_id[experiment_id])
        retrieved.append(
            {
                "rank": rank,
                "chunk_id": experiment_id,
                "page_number": page_number,
                "source_type": metadata.get("source_type"),
                "distance": round(distance, 6),
                "relevant": page_number in expected_pages,
                "accepted": distance <= MAX_DISTANCE,
            }
        )

    pages = [item["page_number"] for item in retrieved]
    accepted_count = sum(1 for item in retrieved if item["accepted"])
    ocr_ranks = [
        item["rank"] for item in retrieved if item["source_type"] == "ocr_figure"
    ]
    row = {
        "retrieved": retrieved,
        "retrieved_pages": pages,
        "accepted_count": accepted_count,
        "contains_ocr_document": bool(ocr_ranks),
        "ocr_rank": ocr_ranks[0] if ocr_ranks else None,
    }
    if question["answerable"]:
        row["hit"] = bool(set(pages).intersection(expected_pages))
        row["precision_at_3"] = precision_at_3(pages, expected_pages)
        row["recall_at_3"] = recall_at_3(pages, expected_pages)
        row["reciprocal_rank"] = reciprocal_rank(pages, expected_pages)
        row["correctly_rejected"] = None
    else:
        row["hit"] = None
        row["precision_at_3"] = None
        row["recall_at_3"] = None
        row["reciprocal_rank"] = None
        row["correctly_rejected"] = accepted_count == 0
    return row


def aggregate(questions, rows):
    answerable = [
        row
        for question, row in zip(questions, rows)
        if question["answerable"]
    ]
    unanswerable = [
        row
        for question, row in zip(questions, rows)
        if not question["answerable"]
    ]
    coverage_hits = sum(1 for row in rows if row["accepted_count"] > 0)
    return {
        "hit_rate": mean([row["hit"] for row in answerable]),
        "precision_at_3": mean([row["precision_at_3"] for row in answerable]),
        "recall_at_3": mean([row["recall_at_3"] for row in answerable]),
        "mrr": mean([row["reciprocal_rank"] for row in answerable]),
        "unanswerable_rejection_rate": mean(
            [row["correctly_rejected"] for row in unanswerable]
        ),
        "retrieval_coverage": coverage_hits / len(rows),
    }


def quality_key(question, row):
    """Higher is better. Answerable questions use hit, then rank, then precision."""

    if question["answerable"]:
        return (
            int(row["hit"]),
            row["reciprocal_rank"],
            row["precision_at_3"],
            row["recall_at_3"],
        )
    return (int(row["correctly_rejected"]),)


def compare_question(question, baseline, expanded):
    baseline_key = quality_key(question, baseline)
    expanded_key = quality_key(question, expanded)
    if expanded_key > baseline_key:
        return "improved"
    if expanded_key < baseline_key:
        return "worse"
    return "unchanged"


def percent(value):
    return f"{value * 100:.1f}%"


def build_report(results):
    baseline = results["aggregate_metrics"]["baseline"]
    expanded = results["aggregate_metrics"]["expanded"]
    changes = results["question_changes"]
    q05 = results["q05"]
    config = results["configuration"]

    lines = [
        "# Candidate pool comparison",
        "",
        f"Generated: {results['timestamp']}",
        f"Dataset: `{results['dataset_id']}`",
        "",
        "## Setup",
        "",
        "Both configurations search the same PDF chunks plus the structured page 4 OCR document.",
        "Vectors are stored in an in-memory Chroma collection. The persistent `gist_documents` collection was not written.",
        "",
        f"- PDF chunks: {results['corpus']['pdf_chunks']}",
        f"- OCR documents: {results['corpus']['ocr_documents']}",
        f"- Final results kept: {config['final_k']}",
        f"- RRF weights: {config['weights'][0]} / {config['weights'][1]}, c={config['rrf_c']}",
        f"- Acceptance gate: squared L2 distance <= {config['max_distance']}",
        "",
        "Hit rate, precision, recall, and MRR use the fused top 3 before the distance gate. That matches the existing retrieval evaluation. Rejection rate and coverage use the distance gate. A chunk is relevant when its page is one of the question's expected pages. The OCR document is page 4, so retrieving it counts as a page 4 hit.",
        "",
        "A question improves when the expanded pool is better on the first metric that differs. For answerable questions that order is hit, reciprocal rank, precision, then recall. For unanswerable questions, correctly rejecting the question is better than accepting a chunk.",
        "",
        "## Aggregate comparison",
        "",
        "| Metric | Baseline (candidate k=3) | Expanded (candidate k=10) |",
        "| --- | ---: | ---: |",
        f"| Hit Rate | {percent(baseline['hit_rate'])} | {percent(expanded['hit_rate'])} |",
        f"| Precision@3 | {percent(baseline['precision_at_3'])} | {percent(expanded['precision_at_3'])} |",
        f"| Recall@3 | {percent(baseline['recall_at_3'])} | {percent(expanded['recall_at_3'])} |",
        f"| MRR | {percent(baseline['mrr'])} | {percent(expanded['mrr'])} |",
        f"| Unanswerable rejection rate | {percent(baseline['unanswerable_rejection_rate'])} | {percent(expanded['unanswerable_rejection_rate'])} |",
        f"| Retrieval coverage | {percent(baseline['retrieval_coverage'])} | {percent(expanded['retrieval_coverage'])} |",
        "",
        "## Question changes",
        "",
        f"- Improved: {len(changes['improved'])} ({format_ids(changes['improved'])})",
        f"- Got worse: {len(changes['worse'])} ({format_ids(changes['worse'])})",
        f"- Unchanged: {len(changes['unchanged'])} ({format_ids(changes['unchanged'])})",
        "",
        "## q05 and the OCR document",
        "",
        q05_sentence("Baseline", q05["baseline"]),
        q05_sentence("Expanded", q05["expanded"]),
        "",
        "## Questions whose top 3 changed",
        "",
    ]
    lines.extend(changed_question_lines(results["questions"]))
    lines.extend(
        [
            "",
            "## Reading the result",
            "",
            comparison_sentence(baseline, expanded),
            "",
            f"Saved `gist_documents` count: {results['persistent_gist_documents']['before']} before, {results['persistent_gist_documents']['after']} after.",
            "",
        ]
    )
    return "\n".join(lines)


def format_ids(question_ids):
    if not question_ids:
        return "none"
    return ", ".join(question_ids)


def q05_sentence(label, row):
    if row["contains_ocr_document"]:
        location = f"retrieves the OCR document at rank {row['ocr_rank']}"
    else:
        location = "does not retrieve the OCR document"
    return (
        f"- **{label}** {location}. "
        f"Retrieved pages: {row['retrieved_pages'] or 'none'}."
    )


def changed_question_lines(questions):
    lines = []
    for item in questions:
        if item["change"] == "unchanged":
            continue
        baseline = item["baseline"]
        expanded = item["expanded"]
        lines.append(
            f"- **{item['question_id']}** {item['change']}. "
            f"Expected pages {item['expected_pages'] or 'none'}. "
            f"Baseline pages {baseline['retrieved_pages'] or 'none'}. "
            f"Expanded pages {expanded['retrieved_pages'] or 'none'}."
        )
    if not lines:
        lines.append("- Every question returned the same top 3 pages.")
    return lines


def comparison_sentence(baseline, expanded):
    labels = (
        ("hit_rate", "Hit rate"),
        ("precision_at_3", "Precision@3"),
        ("recall_at_3", "Recall@3"),
        ("mrr", "MRR"),
        ("unanswerable_rejection_rate", "Unanswerable rejection"),
        ("retrieval_coverage", "Retrieval coverage"),
    )
    sentences = []
    for key, label in labels:
        if expanded[key] > baseline[key]:
            sentences.append(
                f"{label} is higher with the expanded pool "
                f"({percent(expanded[key])} vs {percent(baseline[key])})."
            )
        elif expanded[key] < baseline[key]:
            sentences.append(
                f"{label} is higher with the baseline pool "
                f"({percent(baseline[key])} vs {percent(expanded[key])})."
            )
        else:
            sentences.append(f"{label} is tied at {percent(baseline[key])}.")
    return " ".join(sentences)


def print_summary(results):
    baseline = results["aggregate_metrics"]["baseline"]
    expanded = results["aggregate_metrics"]["expanded"]
    changes = results["question_changes"]
    print("\n=== CANDIDATE POOL COMPARISON ===")
    print(f"{'Metric':<28} {'k=3':>10} {'k=10':>10}")
    for label, key in (
        ("Hit rate", "hit_rate"),
        ("Precision@3", "precision_at_3"),
        ("Recall@3", "recall_at_3"),
        ("MRR", "mrr"),
        ("Unanswerable rejection", "unanswerable_rejection_rate"),
        ("Retrieval coverage", "retrieval_coverage"),
    ):
        print(
            f"{label:<28} {percent(baseline[key]):>10} {percent(expanded[key]):>10}"
        )
    print(
        f"\nImproved {len(changes['improved'])}, "
        f"worse {len(changes['worse'])}, "
        f"unchanged {len(changes['unchanged'])}."
    )
    q05 = results["q05"]
    print(
        "q05 OCR document: "
        f"baseline rank {q05['baseline']['ocr_rank']}, "
        f"expanded rank {q05['expanded']['ocr_rank']}."
    )
    print(f"\nResults: {JSON_PATH}")
    print(f"Report:  {REPORT_PATH}")


def main():
    count_before = persistent_collection_count()
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    questions = dataset["questions"]
    validate_questions(questions)
    if len(questions) != 17:
        raise RuntimeError(f"Expected 17 evaluation questions, found {len(questions)}")

    print("Extracting and chunking the Meridian PDF...")
    pdf_chunks, corpus = build_corpus()
    require_expected_pages(questions, pdf_chunks)
    print(
        f"Shared corpus: {len(pdf_chunks)} PDF chunks + "
        f"{sum(1 for doc in corpus if doc.metadata['source_type'] == 'ocr_figure')} "
        "OCR document."
    )

    embedding_service = EmbeddingService()
    print("Embedding the shared corpus into an in-memory collection...")
    bm25_retriever, semantic_retriever, hybrid_retriever, vector_store = (
        build_retrievers(corpus, embedding_service)
    )
    embeddings_by_id = load_embeddings(vector_store, corpus)
    if hybrid_retriever.weights != WEIGHTS:
        raise RuntimeError(f"Unexpected RRF weights: {hybrid_retriever.weights}")

    per_question = []
    for index, question in enumerate(questions, start=1):
        print(f"[{index}/{len(questions)}] {question['question_id']}")
        query_embedding = embedding_service.embed_query(question["question"])
        scored = {}
        for name, candidate_k in CONFIGS:
            documents = search(
                question["question"],
                candidate_k,
                bm25_retriever,
                semantic_retriever,
                hybrid_retriever,
            )
            scored[name] = score_results(
                question,
                documents,
                query_embedding,
                embeddings_by_id,
            )
        change = compare_question(question, scored["baseline"], scored["expanded"])
        per_question.append(
            {
                "question_id": question["question_id"],
                "question": question["question"],
                "answerable": question["answerable"],
                "question_type": question["question_type"],
                "expected_pages": question["expected_pages"],
                "change": change,
                "baseline": scored["baseline"],
                "expanded": scored["expanded"],
            }
        )

    changes = {
        "improved": [
            item["question_id"]
            for item in per_question
            if item["change"] == "improved"
        ],
        "worse": [
            item["question_id"]
            for item in per_question
            if item["change"] == "worse"
        ],
        "unchanged": [
            item["question_id"]
            for item in per_question
            if item["change"] == "unchanged"
        ],
    }
    if len(changes["improved"]) + len(changes["worse"]) + len(changes["unchanged"]) != len(questions):
        raise RuntimeError("Question change counts do not cover every question")

    q05 = next(item for item in per_question if item["question_id"] == "q05")
    count_after = persistent_collection_count()
    if count_before != count_after:
        raise RuntimeError(
            "The persistent Chroma collection changed during the experiment: "
            f"{count_before} before, {count_after} after"
        )

    results = {
        "timestamp": utc_timestamp(),
        "dataset_id": dataset["dataset_id"],
        "source_pdf": dataset["source_pdf"],
        "answerable_questions": sum(1 for item in questions if item["answerable"]),
        "unanswerable_questions": sum(1 for item in questions if not item["answerable"]),
        "corpus": {
            "pdf_chunks": len(pdf_chunks),
            "ocr_documents": 1,
            "total_documents": len(corpus),
            "ocr_source": str(OCR_PATH.relative_to(BACKEND_ROOT)),
            "vector_collection": "in-memory candidate_pool_experiment",
        },
        "persistent_gist_documents": {
            "before": count_before,
            "after": count_after,
        },
        "configuration": {
            "final_k": FINAL_K,
            "baseline_candidate_k": BASELINE_CANDIDATE_K,
            "expanded_candidate_k": EXPANDED_CANDIDATE_K,
            "weights": WEIGHTS,
            "rrf_c": hybrid_retriever.c,
            "max_distance": MAX_DISTANCE,
            "distance_metric": "squared L2, matching Chroma's default space",
            "embedding_model": "nomic-embed-text",
            "llm_used": False,
        },
        "aggregate_metrics": {
            "baseline": aggregate(questions, [item["baseline"] for item in per_question]),
            "expanded": aggregate(questions, [item["expanded"] for item in per_question]),
        },
        "question_changes": changes,
        "q05": {
            "question": q05["question"],
            "expected_pages": q05["expected_pages"],
            "baseline": {
                "contains_ocr_document": q05["baseline"]["contains_ocr_document"],
                "ocr_rank": q05["baseline"]["ocr_rank"],
                "retrieved_pages": q05["baseline"]["retrieved_pages"],
                "hit": q05["baseline"]["hit"],
            },
            "expanded": {
                "contains_ocr_document": q05["expanded"]["contains_ocr_document"],
                "ocr_rank": q05["expanded"]["ocr_rank"],
                "retrieved_pages": q05["expanded"]["retrieved_pages"],
                "hit": q05["expanded"]["hit"],
            },
        },
        "questions": per_question,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    REPORT_PATH.write_text(build_report(results), encoding="utf-8")
    print_summary(results)


if __name__ == "__main__":
    main()
