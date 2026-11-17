"""Compare semantic-only retrieval with hybrid retrieval.

This module scores retrieval quality. It does not generate answers and it does
not change how VectorStore or HybridSearchService retrieve documents.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


SEMANTIC = "semantic"
HYBRID = "hybrid"
SYSTEMS = (SEMANTIC, HYBRID)

# Shown on the metric chart, in display order.
METRIC_LABELS = [
    ("hit_rate", "Hit Rate"),
    ("precision_at_3", "Precision@3"),
    ("recall_at_3", "Recall@3"),
    ("mrr", "MRR"),
    ("unanswerable_rejection_rate", "Rejection Rate"),
]

SEMANTIC_COLOR = "#4C78A8"
HYBRID_COLOR = "#F58518"
CORRECT_COLOR = "#2E7D32"
INCORRECT_COLOR = "#C62828"

# The project already compared these in test_retrieval_evaluation.py.
# 0.75 is the VectorStore default and the threshold used for reported metrics.
SENSITIVITY_THRESHOLDS = (0.65, 0.75, 0.85)


def squared_l2(left, right):
    """Squared Euclidean distance, which is Chroma's default L2 space."""

    if len(left) != len(right):
        raise ValueError(
            f"Embedding lengths differ: {len(left)} and {len(right)}"
        )
    return sum((a - b) ** 2 for a, b in zip(left, right))


def chunk_id_from_metadata(metadata, question_id, system_name):
    """Rebuild the id VectorStore writes: '{document_id}_{chunk_index}'."""

    if "chunk_index" not in metadata or metadata["chunk_index"] is None:
        raise KeyError(
            f"{system_name} result for {question_id} is missing chunk_index"
        )
    document_id = metadata.get("document_id") or "meridian"
    return f"{document_id}_{int(metadata['chunk_index'])}"


def page_number_from_metadata(metadata, question_id, system_name):
    if "page_number" not in metadata or metadata["page_number"] is None:
        raise KeyError(
            f"{system_name} result for {question_id} is missing page_number"
        )
    return int(metadata["page_number"])


def load_stored_embeddings(collection):
    """Load chunk embeddings once so later distance checks do not re-embed."""

    stored = collection.get(include=["embeddings"])
    embeddings = {}
    for chunk_id, vector in zip(stored["ids"], stored["embeddings"]):
        embeddings[chunk_id] = [float(value) for value in vector]
    if not embeddings:
        raise RuntimeError("Chroma collection gist_documents has no embeddings")
    return embeddings


def verify_distance_matches_chroma(collection, embeddings_by_id):
    """Fail early if our distance does not match the distance Chroma returns."""

    chunk_id = next(iter(embeddings_by_id))
    vector = embeddings_by_id[chunk_id]
    queried = collection.query(
        query_embeddings=[vector],
        n_results=1,
        include=["distances"],
    )
    chroma_distance = float(queried["distances"][0][0])
    manual_distance = squared_l2(vector, vector)
    if abs(chroma_distance - manual_distance) > 1e-4:
        raise RuntimeError(
            "Squared L2 does not match Chroma's distance "
            f"(chroma={chroma_distance}, manual={manual_distance})"
        )


def precision_at_3(retrieved_pages, expected_pages):
    """Relevant retrieved chunks divided by how many chunks were retrieved.

    The denominator is at most 3 because callers pass the top-k list.
    An empty retrieval scores 0 instead of dividing by zero.
    """

    if not retrieved_pages:
        return 0.0
    relevant = sum(1 for page in retrieved_pages if page in expected_pages)
    return relevant / len(retrieved_pages)


def recall_at_3(retrieved_pages, expected_pages):
    """Share of the expected pages that appear at least once in the top 3."""

    if not expected_pages:
        return 0.0
    found = set(retrieved_pages).intersection(expected_pages)
    return len(found) / len(expected_pages)


def reciprocal_rank(retrieved_pages, expected_pages):
    """1 / rank of the first relevant chunk, or 0 when none of the top 3 hit."""

    for rank, page in enumerate(retrieved_pages, start=1):
        if page in expected_pages:
            return 1.0 / rank
    return 0.0


def mean(values):
    if not values:
        raise ValueError("Cannot average an empty list")
    return sum(values) / len(values)


def validate_questions(questions):
    """Check the labeled dataset before any retrieval work starts."""

    if len(questions) < 12:
        raise ValueError(
            f"Evaluation dataset needs at least 12 questions, found {len(questions)}"
        )

    seen_ids = set()
    unanswerable = 0
    for question in questions:
        question_id = question["question_id"]
        if question_id in seen_ids:
            raise ValueError(f"Duplicate question_id: {question_id}")
        seen_ids.add(question_id)

        expected_pages = question["expected_pages"]
        if question["answerable"]:
            if not expected_pages:
                raise ValueError(
                    f"{question_id} is answerable but has no expected pages"
                )
        else:
            unanswerable += 1
            if expected_pages:
                raise ValueError(
                    f"{question_id} is unanswerable but lists expected pages"
                )

    if unanswerable < 3:
        raise ValueError(
            f"Evaluation dataset needs at least 3 unanswerable questions, found {unanswerable}"
        )


def _candidate(rank, chunk_id, page_number, distance, relevant):
    return {
        "rank": rank,
        "chunk_id": chunk_id,
        "page_number": page_number,
        "distance": round(distance, 6),
        "relevant": relevant,
    }


def score_system(question, retrieved, rejected, latencies):
    """Turn one system's retrieved and rejected chunks into metric fields."""

    expected_pages = set(question["expected_pages"])
    retrieved_pages = [item["page_number"] for item in retrieved]
    accepted = [item for item in retrieved if item["accepted"]]

    result = {
        "retrieved": retrieved,
        "rejected": rejected,
        "retrieved_pages": retrieved_pages,
        "retrieved_chunk_ids": [item["chunk_id"] for item in retrieved],
        "accepted_chunk_ids": [item["chunk_id"] for item in accepted],
        "accepted_count": len(accepted),
        "latency_seconds": {
            "runs": [round(value, 6) for value in latencies],
            "average": round(mean(latencies), 6),
        },
    }

    if question["answerable"]:
        result["hit"] = bool(set(retrieved_pages).intersection(expected_pages))
        result["precision_at_3"] = round(
            precision_at_3(retrieved_pages, expected_pages), 6
        )
        result["recall_at_3"] = round(
            recall_at_3(retrieved_pages, expected_pages), 6
        )
        result["reciprocal_rank"] = round(
            reciprocal_rank(retrieved_pages, expected_pages), 6
        )
        result["correctly_rejected"] = None
    else:
        # Ranking metrics are only defined for answerable questions.
        result["hit"] = None
        result["precision_at_3"] = None
        result["recall_at_3"] = None
        result["reciprocal_rank"] = None
        result["correctly_rejected"] = len(accepted) == 0

    return result


def aggregate_metrics(question_results):
    """Average the per-question scores separately for each retrieval system."""

    summary = {}
    all_questions = question_results
    answerable = [item for item in question_results if item["answerable"]]
    unanswerable = [item for item in question_results if not item["answerable"]]

    for system_name in SYSTEMS:
        system_rows = [item["systems"][system_name] for item in answerable]
        rejection_rows = [item["systems"][system_name] for item in unanswerable]
        coverage_hits = sum(
            1
            for item in all_questions
            if item["systems"][system_name]["accepted_count"] > 0
        )
        summary[system_name] = {
            "hit_rate": mean([row["hit"] for row in system_rows]),
            "precision_at_3": mean(
                [row["precision_at_3"] for row in system_rows]
            ),
            "recall_at_3": mean([row["recall_at_3"] for row in system_rows]),
            "mrr": mean([row["reciprocal_rank"] for row in system_rows]),
            "unanswerable_rejection_rate": mean(
                [row["correctly_rejected"] for row in rejection_rows]
            ),
            "retrieval_coverage": coverage_hits / len(all_questions),
            "average_latency_seconds": mean(
                [
                    item["systems"][system_name]["latency_seconds"]["average"]
                    for item in all_questions
                ]
            ),
        }
    return summary


def rejection_rate_at_threshold(question_results, threshold):
    """Recompute unanswerable rejection from stored distances.

    This does not retrieve again. It shows how sensitive the preliminary
    gate is to thresholds the project had already compared.
    """

    rates = {}
    unanswerable = [item for item in question_results if not item["answerable"]]
    for system_name in SYSTEMS:
        correct = 0
        for item in unanswerable:
            # Semantic candidates include chunks the distance filter removed.
            # Hybrid candidates are the RRF top-k, judged by distance afterward.
            candidates = item["systems"][system_name]["distance_candidates"]
            accepted = [
                candidate
                for candidate in candidates
                if candidate["distance"] <= threshold
            ]
            if not accepted:
                correct += 1
        rates[system_name] = correct / len(unanswerable)
    return rates


def _percent(value):
    return f"{value * 100:.1f}%"


def _label_bars(axis, bars, as_percent):
    for bar in bars:
        height = bar.get_height()
        label = _percent(height) if as_percent else f"{height:.3f}"
        axis.annotate(
            label,
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def save_charts(results, output_dir):
    """Write the five required matplotlib charts. Returns their file names."""

    output_dir.mkdir(parents=True, exist_ok=True)
    questions = results["questions"]
    metrics = results["aggregate_metrics"]
    paths = {
        "metric_comparison": output_dir / "metric_comparison.png",
        "question_hit_rate": output_dir / "question_hit_rate.png",
        "precision_at_3": output_dir / "precision_at_3.png",
        "rejection_outcomes": output_dir / "rejection_outcomes.png",
        "retrieval_latency": output_dir / "retrieval_latency.png",
    }

    _chart_metric_comparison(metrics, paths["metric_comparison"])
    _chart_hit_rate(questions, paths["question_hit_rate"])
    _chart_precision(questions, paths["precision_at_3"])
    _chart_rejection(questions, paths["rejection_outcomes"])
    _chart_latency(metrics, paths["retrieval_latency"])

    for path in paths.values():
        if not path.exists():
            raise RuntimeError(f"Chart was not written: {path}")
    return {name: path.name for name, path in paths.items()}


def _chart_metric_comparison(metrics, path):
    labels = [label for _, label in METRIC_LABELS]
    semantic_values = [metrics[SEMANTIC][key] for key, _ in METRIC_LABELS]
    hybrid_values = [metrics[HYBRID][key] for key, _ in METRIC_LABELS]
    positions = range(len(labels))
    width = 0.36

    figure, axis = plt.subplots(figsize=(10, 5.5))
    semantic_bars = axis.bar(
        [pos - width / 2 for pos in positions],
        semantic_values,
        width,
        label="Semantic-only",
        color=SEMANTIC_COLOR,
    )
    hybrid_bars = axis.bar(
        [pos + width / 2 for pos in positions],
        hybrid_values,
        width,
        label="Hybrid",
        color=HYBRID_COLOR,
    )
    _label_bars(axis, semantic_bars, as_percent=True)
    _label_bars(axis, hybrid_bars, as_percent=True)
    axis.set_ylabel("Score")
    axis.set_ylim(0, 1.15)
    axis.set_xticks(list(positions))
    axis.set_xticklabels(labels)
    axis.set_title("Semantic-only vs hybrid retrieval")
    axis.legend()
    axis.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: _percent(value)))
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _chart_hit_rate(questions, path):
    answerable = [item for item in questions if item["answerable"]]
    labels = [item["question_id"] for item in answerable]
    positions = range(len(labels))
    width = 0.36
    semantic_values = [
        1 if item["systems"][SEMANTIC]["hit"] else 0 for item in answerable
    ]
    hybrid_values = [
        1 if item["systems"][HYBRID]["hit"] else 0 for item in answerable
    ]

    figure, axis = plt.subplots(figsize=(11, 5.5))
    semantic_bars = axis.bar(
        [pos - width / 2 for pos in positions],
        semantic_values,
        width,
        label="Semantic-only",
        color=SEMANTIC_COLOR,
    )
    hybrid_bars = axis.bar(
        [pos + width / 2 for pos in positions],
        hybrid_values,
        width,
        label="Hybrid",
        color=HYBRID_COLOR,
    )
    _label_bars(axis, semantic_bars, as_percent=True)
    _label_bars(axis, hybrid_bars, as_percent=True)
    axis.set_ylabel("Hit (at least one expected page)")
    axis.set_ylim(0, 1.25)
    axis.set_yticks([0, 1])
    axis.set_yticklabels(["Miss", "Hit"])
    axis.set_xticks(list(positions))
    axis.set_xticklabels(labels, rotation=45, ha="right")
    axis.set_title("Did retrieval include an expected page?")
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _chart_precision(questions, path):
    answerable = [item for item in questions if item["answerable"]]
    labels = [item["question_id"] for item in answerable]
    positions = range(len(labels))
    width = 0.36
    semantic_values = [
        item["systems"][SEMANTIC]["precision_at_3"] for item in answerable
    ]
    hybrid_values = [
        item["systems"][HYBRID]["precision_at_3"] for item in answerable
    ]
    hybrid_colors = []
    for semantic_value, hybrid_value in zip(semantic_values, hybrid_values):
        if hybrid_value > semantic_value:
            hybrid_colors.append("#2E7D32")
        elif hybrid_value < semantic_value:
            hybrid_colors.append("#C62828")
        else:
            hybrid_colors.append("#9E9E9E")

    figure, axis = plt.subplots(figsize=(11, 5.5))
    semantic_bars = axis.bar(
        [pos - width / 2 for pos in positions],
        semantic_values,
        width,
        label="Semantic-only",
        color=SEMANTIC_COLOR,
    )
    hybrid_bars = axis.bar(
        [pos + width / 2 for pos in positions],
        hybrid_values,
        width,
        color=hybrid_colors,
    )
    _label_bars(axis, semantic_bars, as_percent=True)
    _label_bars(axis, hybrid_bars, as_percent=True)
    axis.bar([], [], color="#2E7D32", label="Hybrid higher")
    axis.bar([], [], color="#C62828", label="Hybrid lower")
    axis.bar([], [], color="#9E9E9E", label="Tie")
    axis.set_ylabel("Precision@3")
    axis.set_ylim(0, 1.25)
    axis.set_xticks(list(positions))
    axis.set_xticklabels(labels, rotation=45, ha="right")
    axis.set_title("Precision@3 by question")
    axis.legend()
    axis.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: _percent(value)))
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _chart_rejection(questions, path):
    unanswerable = [item for item in questions if not item["answerable"]]
    labels = [item["question_id"] for item in unanswerable]
    positions = range(len(labels))
    width = 0.36

    def colors(system_name):
        return [
            CORRECT_COLOR
            if item["systems"][system_name]["correctly_rejected"]
            else INCORRECT_COLOR
            for item in unanswerable
        ]

    figure, axis = plt.subplots(figsize=(8, 5))
    semantic_bars = axis.bar(
        [pos - width / 2 for pos in positions],
        [1] * len(labels),
        width,
        color=colors(SEMANTIC),
        edgecolor=SEMANTIC_COLOR,
        linewidth=2,
    )
    hybrid_bars = axis.bar(
        [pos + width / 2 for pos in positions],
        [1] * len(labels),
        width,
        color=colors(HYBRID),
        edgecolor=HYBRID_COLOR,
        linewidth=2,
    )
    for bar, item in zip(semantic_bars, unanswerable):
        _rejection_label(axis, bar, item["systems"][SEMANTIC]["correctly_rejected"])
    for bar, item in zip(hybrid_bars, unanswerable):
        _rejection_label(axis, bar, item["systems"][HYBRID]["correctly_rejected"])
    axis.legend(
        handles=[
            Patch(
                facecolor="white",
                edgecolor=SEMANTIC_COLOR,
                linewidth=2,
                label="Semantic-only",
            ),
            Patch(
                facecolor="white",
                edgecolor=HYBRID_COLOR,
                linewidth=2,
                label="Hybrid",
            ),
            Patch(facecolor=CORRECT_COLOR, label="Correctly rejected"),
            Patch(facecolor=INCORRECT_COLOR, label="Incorrectly accepted"),
        ]
    )
    axis.set_ylim(0, 1.35)
    axis.set_yticks([])
    axis.set_xticks(list(positions))
    axis.set_xticklabels(labels)
    axis.set_title("Unanswerable questions: rejected or accepted")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _rejection_label(axis, bar, correctly_rejected):
    axis.annotate(
        "Rejected" if correctly_rejected else "Accepted",
        xy=(bar.get_x() + bar.get_width() / 2, 0.5),
        ha="center",
        va="center",
        color="white",
        fontsize=8,
        fontweight="bold",
    )


def _chart_latency(metrics, path):
    labels = ["Semantic-only", "Hybrid"]
    values = [
        metrics[SEMANTIC]["average_latency_seconds"],
        metrics[HYBRID]["average_latency_seconds"],
    ]
    figure, axis = plt.subplots(figsize=(6.5, 5))
    bars = axis.bar(labels, values, color=[SEMANTIC_COLOR, HYBRID_COLOR])
    for bar, value in zip(bars, values):
        axis.annotate(
            f"{value:.3f}s",
            xy=(bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )
    axis.set_ylabel("Average seconds per question")
    axis.set_ylim(0, max(values) * 1.25 if max(values) else 1)
    axis.set_title("Average retrieval latency")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def build_report(results):
    """Explain the measured comparison. Numbers come only from this run."""

    metrics = results["aggregate_metrics"]
    semantic = metrics[SEMANTIC]
    hybrid = metrics[HYBRID]
    questions = results["questions"]
    config = results["configuration"]

    lines = [
        "# Retrieval evaluation report",
        "",
        f"Generated: {results['timestamp']}",
        f"Dataset: `{results['dataset_id']}`",
        "",
        "## What was evaluated",
        "",
        "This run compares two retrievers on the same Meridian PDF chunks and the same labeled questions.",
        "",
        "- **Semantic-only** embeds the question with `nomic-embed-text` and searches the `gist_documents` Chroma collection. Chunks farther than the configured squared L2 distance are dropped before scoring.",
        "- **Hybrid** uses the existing `HybridSearchService`: BM25 and Chroma semantic search, fused with Reciprocal Rank Fusion at weights "
        f"{config['hybrid_rrf_weights']}. Ranking metrics use the top {config['top_k']} fused chunks. RRF scores are not treated as confidence.",
        "- The LLM was not called. Latency covers retrieval only, after one untimed warmup query per system. PDF extraction and chunking are excluded.",
        "",
        "A retrieved chunk counts as relevant when its `page_number` is one of the question's expected pages. Those pages were labeled from the extracted PDF before this run.",
        "",
        "## How the metrics are calculated",
        "",
        "Answerable-question metrics use the chunks each system kept for ranking.",
        "",
        "- **Hit Rate** is the share of answerable questions with at least one expected page in the retrieved chunks.",
        "- **Precision@3** is, for each question, relevant retrieved chunks divided by retrieved chunks (at most 3). Empty retrieval scores 0. The reported value is the average.",
        "- **Recall@3** is, for each question, the share of its expected pages that appear at least once. The reported value is the average.",
        "- **MRR** is the average of 1/rank for the first relevant chunk. A complete miss scores 0.",
        "- **Unanswerable Rejection Rate** is the share of unanswerable questions with no accepted chunk.",
        "- **Retrieval Coverage** is the share of all questions, answerable and unanswerable, with at least one accepted chunk. It is not the hit rate.",
        "",
        "### Preliminary hybrid rejection gate",
        "",
        "Hybrid search always returns ranked chunks, so rank alone cannot reject an unanswerable question. The gate used here is separate from RRF:",
        "",
        f"a hybrid chunk is **accepted** only when its Chroma squared L2 distance to the query embedding is at most **{config['max_distance']}**.",
        "",
        "That threshold is the existing `VectorStore` default. `test_retrieval_evaluation.py` had already compared 0.65, 0.75, and 0.85. This run does not pick a new threshold to maximize the score. The sensitivity table below recomputes rejection from the stored distances.",
        "",
        "Semantic-only uses the same distance threshold inside `VectorStore.search`, so its retrieved chunks and its accepted chunks are the same list.",
        "",
        "## Aggregate comparison",
        "",
        "| Metric | Semantic-only | Hybrid |",
        "| --- | ---: | ---: |",
    ]

    for key, label in METRIC_LABELS:
        lines.append(
            f"| {label} | {_percent(semantic[key])} | {_percent(hybrid[key])} |"
        )
    lines.append(
        f"| Retrieval coverage | {_percent(semantic['retrieval_coverage'])} | {_percent(hybrid['retrieval_coverage'])} |"
    )
    lines.append(
        f"| Average latency | {semantic['average_latency_seconds']:.3f}s | {hybrid['average_latency_seconds']:.3f}s |"
    )

    lines.extend(
        [
            "",
            comparison_paragraph(semantic, hybrid),
            "",
            "### Rejection-threshold sensitivity",
            "",
            "Official rejection rates use "
            f"{config['max_distance']}. The other rows only re-filter stored distances.",
            "",
            "| Threshold | Semantic-only rejection | Hybrid rejection |",
            "| ---: | ---: | ---: |",
        ]
    )
    for threshold, rates in results["rejection_sensitivity"].items():
        marker = " (reported)" if float(threshold) == config["max_distance"] else ""
        lines.append(
            f"| {threshold}{marker} | {_percent(rates[SEMANTIC])} | {_percent(rates[HYBRID])} |"
        )

    lines.extend(["", "## Per-question differences", ""])
    lines.extend(question_difference_lines(questions))
    lines.extend(["", "## Questions each system struggled with", ""])
    lines.extend(struggle_lines(questions))
    lines.extend(distance_gate_lines(questions))
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            f"- The labeled set has {results['answerable_questions']} answerable and {results['unanswerable_questions']} unanswerable questions, all from one 14-page paper. Small differences can come from one or two questions.",
            "- Relevance is judged at page level. A chunk from the right page can still omit the exact sentence, and a chunk from another page can mention the same terms.",
            "- Semantic chunk boundaries depend on `nomic-embed-text`. A later chunking run can move a sentence onto a different chunk even when the page label stays valid.",
            "- Ollama embeddings are not guaranteed to be bitwise identical across calls. Ranking used the first timed run. Latency is the average of "
            f"{config['latency_repetitions']} timed runs after one warmup.",
            "- The hybrid acceptance gate reuses squared L2 distance because this project already had that threshold. It is a preliminary confidence check, not a trained rejection model, and it is not applied to RRF scores.",
            "- `HybridSearchService` asks each retriever for 3 chunks and fuses them with RRF constant c="
            f"{config['hybrid_rrf_c']}. The evaluator then keeps the first {config['top_k']} fused chunks.",
            "",
            "## Recommended next improvements",
            "",
            "- Add more labeled questions, including ones whose answers share wording with nearby but wrong pages.",
            "- Judge relevance on chunk text, not only page number, once the chunk set is stable.",
            "- Tune the hybrid rejection gate on a separate set of questions, then freeze it before the next report.",
            "- Record the RRF rank of the first relevant chunk beside MRR so keyword wins and semantic wins can be told apart.",
            "",
            "## Charts",
            "",
        ]
    )
    for name, filename in results["charts"].items():
        lines.append(f"- [{name}](./{filename})")
    lines.append("")
    return "\n".join(lines)


def comparison_paragraph(semantic, hybrid):
    """State which system scored higher only where the averages differ."""

    sentences = []
    labels = {
        "hit_rate": "Hit rate",
        "precision_at_3": "Precision@3",
        "recall_at_3": "Recall@3",
        "mrr": "MRR",
        "unanswerable_rejection_rate": "Unanswerable rejection",
    }
    for key, label in labels.items():
        if hybrid[key] > semantic[key]:
            sentences.append(
                f"{label} is higher for hybrid ({_percent(hybrid[key])} vs {_percent(semantic[key])})."
            )
        elif hybrid[key] < semantic[key]:
            sentences.append(
                f"{label} is higher for semantic-only ({_percent(semantic[key])} vs {_percent(hybrid[key])})."
            )
        else:
            sentences.append(f"{label} is tied at {_percent(semantic[key])}.")

    semantic_latency = semantic["average_latency_seconds"]
    hybrid_latency = hybrid["average_latency_seconds"]
    if abs(semantic_latency - hybrid_latency) < 0.05:
        sentences.append(
            f"Average latency is {semantic_latency:.3f}s for semantic-only and "
            f"{hybrid_latency:.3f}s for hybrid. The gap is a few milliseconds "
            "after warmup, so this run does not show a meaningful speed difference."
        )
    elif hybrid_latency < semantic_latency:
        sentences.append(
            f"Hybrid is faster on average ({hybrid_latency:.3f}s vs {semantic_latency:.3f}s)."
        )
    else:
        sentences.append(
            f"Semantic-only is faster on average ({semantic_latency:.3f}s vs {hybrid_latency:.3f}s)."
        )
    return " ".join(sentences)


def question_difference_lines(questions):
    """List answerable questions where hit or precision differs."""

    lines = []
    for item in questions:
        if not item["answerable"]:
            continue
        semantic = item["systems"][SEMANTIC]
        hybrid = item["systems"][HYBRID]
        if (
            semantic["hit"] == hybrid["hit"]
            and semantic["precision_at_3"] == hybrid["precision_at_3"]
            and semantic["retrieved_pages"] == hybrid["retrieved_pages"]
        ):
            continue
        lines.append(
            f"- **{item['question_id']}** ({item['question_type']}). "
            f"Expected pages {item['expected_pages']}. "
            f"Semantic retrieved {semantic['retrieved_pages'] or 'nothing'} "
            f"(precision {_percent(semantic['precision_at_3'])}, "
            f"recall {_percent(semantic['recall_at_3'])}). "
            f"Hybrid retrieved {hybrid['retrieved_pages'] or 'nothing'} "
            f"(precision {_percent(hybrid['precision_at_3'])}, "
            f"recall {_percent(hybrid['recall_at_3'])})."
        )
    if not lines:
        lines.append("- The two systems retrieved the same pages for every answerable question.")
    return lines


def struggle_lines(questions):
    lines = []
    for system_name, title in (
        (SEMANTIC, "Semantic-only"),
        (HYBRID, "Hybrid"),
    ):
        misses = [
            item["question_id"]
            for item in questions
            if item["answerable"] and not item["systems"][system_name]["hit"]
        ]
        partial = [
            item["question_id"]
            for item in questions
            if item["answerable"]
            and item["systems"][system_name]["hit"]
            and item["systems"][system_name]["recall_at_3"] < 1
        ]
        false_accepts = [
            item["question_id"]
            for item in questions
            if not item["answerable"]
            and not item["systems"][system_name]["correctly_rejected"]
        ]
        lines.append(f"**{title}**")
        lines.append(
            "- Missed the expected page: "
            + (", ".join(misses) if misses else "none")
            + "."
        )
        lines.append(
            "- Hit only some expected pages: "
            + (", ".join(partial) if partial else "none")
            + "."
        )
        lines.append(
            "- Accepted an unanswerable question: "
            + (", ".join(false_accepts) if false_accepts else "none")
            + "."
        )
        lines.append("")
    return lines


def distance_gate_lines(questions):
    """Explain hits that ranking counted but the distance gate did not accept."""

    lines = ["### Ranking hits the distance gate rejected", ""]
    found = False
    for item in questions:
        if not item["answerable"]:
            continue
        for system_name, title in ((SEMANTIC, "Semantic-only"), (HYBRID, "Hybrid")):
            row = item["systems"][system_name]
            if row["hit"] and row["accepted_count"] == 0:
                found = True
                lines.append(
                    f"- **{item['question_id']}** ({title}) retrieved expected "
                    f"page(s) {row['retrieved_pages']}, but every chunk was farther "
                    "than the squared L2 cutoff, so none were accepted. "
                    "Hit rate still counts this question. Coverage does not."
                )
    if not found:
        lines.append(
            "- No answerable question was a ranking hit with zero accepted chunks."
        )
    lines.append("")
    return lines


def write_outputs(results, output_dir):
    """Save the JSON results, charts, and Markdown report.

    The JSON is written before the charts so a plotting error does not
    discard the retrieval scores.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "evaluation_results.json"
    results["charts"] = {}
    _write_json(json_path, results)

    results["charts"] = save_charts(results, output_dir)
    report_path = output_dir / "evaluation_report.md"
    report_path.write_text(build_report(results), encoding="utf-8")
    _write_json(json_path, results)
    return json_path, report_path


def _write_json(path, results):
    path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def utc_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
