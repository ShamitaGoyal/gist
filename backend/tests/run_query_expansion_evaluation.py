"""Compare hybrid retrieval with and without one LLM query rewrite.

Both configurations search the same in-memory corpus: the PDF chunks plus the
structured page 4 OCR document. Each retriever contributes 10 candidates, RRF
weights stay 0.5/0.5, and the fused top 3 are scored. The saved gist_documents
collection is only read.

The rewrite comes from the existing local Ollama model. The original question
remains the labeled question. Relevance labels are not changed.

Run from the backend directory:

    python3 tests/run_query_expansion_evaluation.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.retrieval_evaluator import utc_timestamp, validate_questions
from run_candidate_pool_comparison import (
    aggregate,
    build_corpus,
    build_retrievers,
    compare_question,
    load_embeddings,
    percent,
    require_expected_pages,
    score_results,
    search,
)
from test_ocr_hybrid_retrieval import OCR_PATH, persistent_collection_count


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = BACKEND_ROOT / "data" / "evaluation_questions.json"
OUTPUT_DIR = BACKEND_ROOT / "data" / "evaluation_results"
JSON_PATH = OUTPUT_DIR / "query_expansion_results.json"
REPORT_PATH = OUTPUT_DIR / "query_expansion_report.md"

CANDIDATE_K = 10
FINAL_K = 3
WEIGHTS = [0.5, 0.5]

EXPANSION_PROMPT = """Rewrite the question into one search query for a document retrieval system.

Rules:
1. Return only the rewritten search query.
2. Preserve the original question's meaning.
3. Include technical terminology and synonyms already implied by the question.
4. Do not answer the question.
5. Do not add facts, names, numbers, or page references that are not in the question.
6. Do not explain the rewrite.

QUESTION:
{question}

SEARCH QUERY:
"""


def expand_query(llm, question_text):
    """Ask the local model for one search query. Record the raw reply."""

    response = llm.model.invoke(EXPANSION_PROMPT.format(question=question_text))
    raw = response.content
    if not isinstance(raw, str):
        raise RuntimeError(f"Query expansion returned a non-text response: {raw!r}")
    expanded = " ".join(raw.split())
    if not expanded:
        raise RuntimeError("Query expansion returned an empty query")
    return raw, expanded


def build_report(results):
    original = results["aggregate_metrics"]["original"]
    expanded = results["aggregate_metrics"]["query_expansion"]
    changes = results["question_changes"]
    q05 = results["q05"]
    corpus = results["corpus"]

    lines = [
        "# Query expansion evaluation",
        "",
        f"Generated: {results['timestamp']}",
        f"Dataset: `{results['dataset_id']}`",
        "",
        "## Setup",
        "",
        "Both configurations search one frozen corpus. The expanded run retrieves with the rewritten query. Relevance labels stay on the original question.",
        "",
        f"- PDF chunks: {corpus['pdf_chunks']}",
        f"- OCR documents: {corpus['ocr_documents']}",
        f"- BM25 candidate k: {results['configuration']['candidate_k']}",
        f"- Semantic candidate k: {results['configuration']['candidate_k']}",
        f"- Final results kept: {results['configuration']['final_k']}",
        f"- RRF weights: 0.5 / 0.5, c={results['configuration']['rrf_c']}",
        f"- Acceptance gate: squared L2 distance <= {results['configuration']['max_distance']} against the query that was searched",
        f"- Expansion model: `{results['configuration']['expansion_model']}` at temperature {results['configuration']['expansion_temperature']}",
        "",
        "Hit rate, precision, recall, and MRR use the fused top 3 before the distance gate. Rejection rate and coverage use the distance gate. A chunk is relevant when its page is one of the original question's expected pages.",
        "",
        "A question improves when query expansion is better on the first metric that differs. For answerable questions that order is hit, reciprocal rank, precision, then recall. For unanswerable questions, correctly rejecting the question is better than accepting a chunk.",
        "",
        "## Aggregate comparison",
        "",
        "| Metric | Original question | Query expansion |",
        "| --- | ---: | ---: |",
        f"| Hit Rate | {percent(original['hit_rate'])} | {percent(expanded['hit_rate'])} |",
        f"| Precision@3 | {percent(original['precision_at_3'])} | {percent(expanded['precision_at_3'])} |",
        f"| Recall@3 | {percent(original['recall_at_3'])} | {percent(expanded['recall_at_3'])} |",
        f"| MRR | {percent(original['mrr'])} | {percent(expanded['mrr'])} |",
        f"| Unanswerable rejection rate | {percent(original['unanswerable_rejection_rate'])} | {percent(expanded['unanswerable_rejection_rate'])} |",
        f"| Retrieval coverage | {percent(original['retrieval_coverage'])} | {percent(expanded['retrieval_coverage'])} |",
        "",
        "## Question changes",
        "",
        f"- Improved: {len(changes['improved'])} ({format_ids(changes['improved'])})",
        f"- Got worse: {len(changes['worse'])} ({format_ids(changes['worse'])})",
        f"- Unchanged: {len(changes['unchanged'])} ({format_ids(changes['unchanged'])})",
        "",
        "## q05 and the OCR document",
        "",
        ocr_sentence("Original question", q05["original"]),
        ocr_sentence("Query expansion", q05["query_expansion"]),
        f"- Expanded query: {q05['expanded_query']}",
        "",
        "## Per-question results",
        "",
        "| Question | Change | Original pages | Expansion pages | Expanded query |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in results["questions"]:
        lines.append(
            "| {question_id} | {change} | {original_pages} | {expanded_pages} | {query} |".format(
                question_id=item["question_id"],
                change=item["change"],
                original_pages=pages_cell(item["original"]["retrieved_pages"]),
                expanded_pages=pages_cell(item["query_expansion"]["retrieved_pages"]),
                query=item["expanded_query"].replace("|", "\\|"),
            )
        )
    lines.extend(
        [
            "",
            "## Reading the result",
            "",
            comparison_sentence(original, expanded),
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


def pages_cell(pages):
    if not pages:
        return "none"
    return ", ".join(str(page) for page in pages)


def ocr_sentence(label, row):
    if row["contains_ocr_document"]:
        location = f"retrieves the OCR document at rank {row['ocr_rank']}"
    else:
        location = "does not retrieve the OCR document"
    return (
        f"- **{label}** {location}. "
        f"Retrieved pages: {row['retrieved_pages'] or 'none'}."
    )


def comparison_sentence(original, expanded):
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
        if expanded[key] > original[key]:
            sentences.append(
                f"{label} is higher with query expansion "
                f"({percent(expanded[key])} vs {percent(original[key])})."
            )
        elif expanded[key] < original[key]:
            sentences.append(
                f"{label} is higher with the original question "
                f"({percent(original[key])} vs {percent(expanded[key])})."
            )
        else:
            sentences.append(f"{label} is tied at {percent(original[key])}.")
    return " ".join(sentences)


def print_summary(results):
    original = results["aggregate_metrics"]["original"]
    expanded = results["aggregate_metrics"]["query_expansion"]
    changes = results["question_changes"]
    print("\n=== QUERY EXPANSION EVALUATION ===")
    print(f"{'Metric':<28} {'Original':>12} {'Expanded':>12}")
    for label, key in (
        ("Hit rate", "hit_rate"),
        ("Precision@3", "precision_at_3"),
        ("Recall@3", "recall_at_3"),
        ("MRR", "mrr"),
        ("Unanswerable rejection", "unanswerable_rejection_rate"),
        ("Retrieval coverage", "retrieval_coverage"),
    ):
        print(
            f"{label:<28} {percent(original[key]):>12} {percent(expanded[key]):>12}"
        )
    print(
        f"\nImproved {len(changes['improved'])}, "
        f"worse {len(changes['worse'])}, "
        f"unchanged {len(changes['unchanged'])}."
    )
    q05 = results["q05"]
    print(
        "q05 OCR document: "
        f"original rank {q05['original']['ocr_rank']}, "
        f"expansion rank {q05['query_expansion']['ocr_rank']}."
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

    print("Extracting and chunking the Meridian PDF once...")
    pdf_chunks, corpus = build_corpus()
    require_expected_pages(questions, pdf_chunks)
    print(
        f"Frozen corpus: {len(pdf_chunks)} PDF chunks + "
        f"{sum(1 for doc in corpus if doc.metadata['source_type'] == 'ocr_figure')} "
        "OCR document."
    )

    embedding_service = EmbeddingService()
    print("Embedding the shared corpus into an in-memory collection...")
    bm25_retriever, semantic_retriever, hybrid_retriever, vector_store = (
        build_retrievers(corpus, embedding_service)
    )
    embeddings_by_id = load_embeddings(vector_store, corpus)
    if list(hybrid_retriever.weights) != WEIGHTS:
        raise RuntimeError(f"Unexpected RRF weights: {hybrid_retriever.weights}")

    llm = LLMService()
    per_question = []
    for index, question in enumerate(questions, start=1):
        print(f"[{index}/{len(questions)}] {question['question_id']}")
        try:
            raw_expansion, expanded_query = expand_query(llm, question["question"])
        except Exception as exc:
            raise RuntimeError(
                f"Query expansion failed for {question['question_id']}: {exc}"
            ) from exc

        original_embedding = embedding_service.embed_query(question["question"])
        original_docs = search(
            question["question"],
            CANDIDATE_K,
            bm25_retriever,
            semantic_retriever,
            hybrid_retriever,
        )
        original_row = score_results(
            question,
            original_docs,
            original_embedding,
            embeddings_by_id,
        )

        expanded_embedding = embedding_service.embed_query(expanded_query)
        expanded_docs = search(
            expanded_query,
            CANDIDATE_K,
            bm25_retriever,
            semantic_retriever,
            hybrid_retriever,
        )
        expanded_row = score_results(
            question,
            expanded_docs,
            expanded_embedding,
            embeddings_by_id,
        )
        per_question.append(
            {
                "question_id": question["question_id"],
                "question": question["question"],
                "answerable": question["answerable"],
                "question_type": question["question_type"],
                "expected_pages": question["expected_pages"],
                "expanded_query_raw": raw_expansion,
                "expanded_query": expanded_query,
                "change": compare_question(question, original_row, expanded_row),
                "original": original_row,
                "query_expansion": expanded_row,
            }
        )

    changes = {
        "improved": [
            item["question_id"] for item in per_question if item["change"] == "improved"
        ],
        "worse": [
            item["question_id"] for item in per_question if item["change"] == "worse"
        ],
        "unchanged": [
            item["question_id"]
            for item in per_question
            if item["change"] == "unchanged"
        ],
    }
    if (
        len(changes["improved"]) + len(changes["worse"]) + len(changes["unchanged"])
        != len(questions)
    ):
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
            "candidate_k": CANDIDATE_K,
            "final_k": FINAL_K,
            "weights": WEIGHTS,
            "rrf_c": hybrid_retriever.c,
            "max_distance": 0.75,
            "distance_metric": "squared L2 against the query sent to retrieval",
            "embedding_model": "nomic-embed-text",
            "expansion_model": llm.model.model,
            "expansion_temperature": llm.model.temperature,
            "expansion_prompt": EXPANSION_PROMPT,
            "llm_answers_generated": False,
        },
        "aggregate_metrics": {
            "original": aggregate(
                questions, [item["original"] for item in per_question]
            ),
            "query_expansion": aggregate(
                questions, [item["query_expansion"] for item in per_question]
            ),
        },
        "question_changes": changes,
        "q05": {
            "question": q05["question"],
            "expanded_query": q05["expanded_query"],
            "expected_pages": q05["expected_pages"],
            "original": {
                "contains_ocr_document": q05["original"]["contains_ocr_document"],
                "ocr_rank": q05["original"]["ocr_rank"],
                "retrieved_pages": q05["original"]["retrieved_pages"],
                "hit": q05["original"]["hit"],
            },
            "query_expansion": {
                "contains_ocr_document": q05["query_expansion"]["contains_ocr_document"],
                "ocr_rank": q05["query_expansion"]["ocr_rank"],
                "retrieved_pages": q05["query_expansion"]["retrieved_pages"],
                "hit": q05["query_expansion"]["hit"],
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
