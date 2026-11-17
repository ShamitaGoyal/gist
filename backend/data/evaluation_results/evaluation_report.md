# Retrieval evaluation report

Generated: 2026-11-17T07:10:12+00:00
Dataset: `meridian-retrieval-v1`

## What was evaluated

This run compares two retrievers on the same Meridian PDF chunks and the same labeled questions.

- **Semantic-only** embeds the question with `nomic-embed-text` and searches the `gist_documents` Chroma collection. Chunks farther than the configured squared L2 distance are dropped before scoring.
- **Hybrid** uses the existing `HybridSearchService`: BM25 and Chroma semantic search, fused with Reciprocal Rank Fusion at weights [0.5, 0.5]. Ranking metrics use the top 3 fused chunks. RRF scores are not treated as confidence.
- The LLM was not called. Latency covers retrieval only, after one untimed warmup query per system. PDF extraction and chunking are excluded.

A retrieved chunk counts as relevant when its `page_number` is one of the question's expected pages. Those pages were labeled from the extracted PDF before this run.

## How the metrics are calculated

Answerable-question metrics use the chunks each system kept for ranking.

- **Hit Rate** is the share of answerable questions with at least one expected page in the retrieved chunks.
- **Precision@3** is, for each question, relevant retrieved chunks divided by retrieved chunks (at most 3). Empty retrieval scores 0. The reported value is the average.
- **Recall@3** is, for each question, the share of its expected pages that appear at least once. The reported value is the average.
- **MRR** is the average of 1/rank for the first relevant chunk. A complete miss scores 0.
- **Unanswerable Rejection Rate** is the share of unanswerable questions with no accepted chunk.
- **Retrieval Coverage** is the share of all questions, answerable and unanswerable, with at least one accepted chunk. It is not the hit rate.

### Preliminary hybrid rejection gate

Hybrid search always returns ranked chunks, so rank alone cannot reject an unanswerable question. The gate used here is separate from RRF:

a hybrid chunk is **accepted** only when its Chroma squared L2 distance to the query embedding is at most **0.75**.

That threshold is the existing `VectorStore` default. `test_retrieval_evaluation.py` had already compared 0.65, 0.75, and 0.85. This run does not pick a new threshold to maximize the score. The sensitivity table below recomputes rejection from the stored distances.

Semantic-only uses the same distance threshold inside `VectorStore.search`, so its retrieved chunks and its accepted chunks are the same list.

## Aggregate comparison

| Metric | Semantic-only | Hybrid |
| --- | ---: | ---: |
| Hit Rate | 64.3% | 92.9% |
| Precision@3 | 38.1% | 52.4% |
| Recall@3 | 64.3% | 92.9% |
| MRR | 59.5% | 78.6% |
| Rejection Rate | 100.0% | 100.0% |
| Retrieval coverage | 76.5% | 76.5% |
| Average latency | 0.022s | 0.020s |

Hit rate is higher for hybrid (92.9% vs 64.3%). Precision@3 is higher for hybrid (52.4% vs 38.1%). Recall@3 is higher for hybrid (92.9% vs 64.3%). MRR is higher for hybrid (78.6% vs 59.5%). Unanswerable rejection is tied at 100.0%. Average latency is 0.022s for semantic-only and 0.020s for hybrid. The gap is a few milliseconds after warmup, so this run does not show a meaningful speed difference.

### Rejection-threshold sensitivity

Official rejection rates use 0.75. The other rows only re-filter stored distances.

| Threshold | Semantic-only rejection | Hybrid rejection |
| ---: | ---: | ---: |
| 0.65 | 100.0% | 100.0% |
| 0.75 (reported) | 100.0% | 100.0% |
| 0.85 | 66.7% | 66.7% |

## Per-question differences

- **q01** (direct_factual). Expected pages [1]. Semantic retrieved [7, 3, 3] (precision 0.0%, recall 0.0%). Hybrid retrieved [1, 7, 2] (precision 33.3%, recall 100.0%).
- **q02** (technical_terminology). Expected pages [2]. Semantic retrieved [1, 9, 13] (precision 0.0%, recall 0.0%). Hybrid retrieved [1, 2, 2] (precision 66.7%, recall 100.0%).
- **q03** (technical_terminology). Expected pages [3]. Semantic retrieved [3, 3, 7] (precision 66.7%, recall 100.0%). Hybrid retrieved [3, 3, 9] (precision 66.7%, recall 100.0%).
- **q04** (relationship). Expected pages [3]. Semantic retrieved [3, 3, 9] (precision 66.7%, recall 100.0%). Hybrid retrieved [9, 3, 3] (precision 66.7%, recall 100.0%).
- **q05** (technical_terminology). Expected pages [4]. Semantic retrieved [6] (precision 0.0%, recall 0.0%). Hybrid retrieved [8, 6, 5] (precision 0.0%, recall 0.0%).
- **q06** (technical_terminology). Expected pages [5]. Semantic retrieved [5, 3, 3] (precision 33.3%, recall 100.0%). Hybrid retrieved [5, 11, 3] (precision 33.3%, recall 100.0%).
- **q07** (meridian_feature). Expected pages [5, 6]. Semantic retrieved [6, 6, 5] (precision 100.0%, recall 100.0%). Hybrid retrieved [6, 5, 6] (precision 100.0%, recall 100.0%).
- **q08** (meridian_feature). Expected pages [6]. Semantic retrieved nothing (precision 0.0%, recall 0.0%). Hybrid retrieved [11, 6, 2] (precision 33.3%, recall 100.0%).
- **q09** (meridian_feature). Expected pages [7]. Semantic retrieved [7, 1, 9] (precision 33.3%, recall 100.0%). Hybrid retrieved [7, 1, 6] (precision 33.3%, recall 100.0%).
- **q10** (relationship). Expected pages [8]. Semantic retrieved [8, 3, 8] (precision 66.7%, recall 100.0%). Hybrid retrieved [8, 9, 7] (precision 33.3%, recall 100.0%).
- **q11** (relationship). Expected pages [9]. Semantic retrieved [7, 3, 9] (precision 33.3%, recall 100.0%). Hybrid retrieved [9, 9, 7] (precision 66.7%, recall 100.0%).
- **q12** (meridian_feature). Expected pages [10]. Semantic retrieved [10, 10, 9] (precision 66.7%, recall 100.0%). Hybrid retrieved [10, 9, 10] (precision 66.7%, recall 100.0%).
- **q13** (multi_section). Expected pages [5, 11]. Semantic retrieved [5, 11, 13] (precision 66.7%, recall 100.0%). Hybrid retrieved [11, 5, 5] (precision 100.0%, recall 100.0%).
- **q14** (relationship). Expected pages [12]. Semantic retrieved [11, 7, 9] (precision 0.0%, recall 0.0%). Hybrid retrieved [11, 12, 9] (precision 33.3%, recall 100.0%).

## Questions each system struggled with

**Semantic-only**
- Missed the expected page: q01, q02, q05, q08, q14.
- Hit only some expected pages: none.
- Accepted an unanswerable question: none.

**Hybrid**
- Missed the expected page: q05.
- Hit only some expected pages: none.
- Accepted an unanswerable question: none.

### Ranking hits the distance gate rejected

- **q08** (Hybrid) retrieved expected page(s) [11, 6, 2], but every chunk was farther than the squared L2 cutoff, so none were accepted. Hit rate still counts this question. Coverage does not.


## Limitations

- The labeled set has 14 answerable and 3 unanswerable questions, all from one 14-page paper. Small differences can come from one or two questions.
- Relevance is judged at page level. A chunk from the right page can still omit the exact sentence, and a chunk from another page can mention the same terms.
- Semantic chunk boundaries depend on `nomic-embed-text`. A later chunking run can move a sentence onto a different chunk even when the page label stays valid.
- Ollama embeddings are not guaranteed to be bitwise identical across calls. Ranking used the first timed run. Latency is the average of 3 timed runs after one warmup.
- The hybrid acceptance gate reuses squared L2 distance because this project already had that threshold. It is a preliminary confidence check, not a trained rejection model, and it is not applied to RRF scores.
- `HybridSearchService` asks each retriever for 3 chunks and fuses them with RRF constant c=60. The evaluator then keeps the first 3 fused chunks.

## Recommended next improvements

- Add more labeled questions, including ones whose answers share wording with nearby but wrong pages.
- Judge relevance on chunk text, not only page number, once the chunk set is stable.
- Tune the hybrid rejection gate on a separate set of questions, then freeze it before the next report.
- Record the RRF rank of the first relevant chunk beside MRR so keyword wins and semantic wins can be told apart.

## Charts

- [metric_comparison](./metric_comparison.png)
- [question_hit_rate](./question_hit_rate.png)
- [precision_at_3](./precision_at_3.png)
- [rejection_outcomes](./rejection_outcomes.png)
- [retrieval_latency](./retrieval_latency.png)
