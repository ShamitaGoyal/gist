# Candidate pool comparison

Generated: 2026-11-18T06:18:58+00:00
Dataset: `meridian-retrieval-v1`

## Setup

Both configurations search the same PDF chunks plus the structured page 4 OCR document.
Vectors are stored in an in-memory Chroma collection. The persistent `gist_documents` collection was not written.

- PDF chunks: 52
- OCR documents: 1
- Final results kept: 3
- RRF weights: 0.5 / 0.5, c=60
- Acceptance gate: squared L2 distance <= 0.75

Hit rate, precision, recall, and MRR use the fused top 3 before the distance gate. That matches the existing retrieval evaluation. Rejection rate and coverage use the distance gate. A chunk is relevant when its page is one of the question's expected pages. The OCR document is page 4, so retrieving it counts as a page 4 hit.

A question improves when the expanded pool is better on the first metric that differs. For answerable questions that order is hit, reciprocal rank, precision, then recall. For unanswerable questions, correctly rejecting the question is better than accepting a chunk.

## Aggregate comparison

| Metric | Baseline (candidate k=3) | Expanded (candidate k=10) |
| --- | ---: | ---: |
| Hit Rate | 92.9% | 85.7% |
| Precision@3 | 50.0% | 50.0% |
| Recall@3 | 89.3% | 82.1% |
| MRR | 85.7% | 82.1% |
| Unanswerable rejection rate | 100.0% | 100.0% |
| Retrieval coverage | 82.4% | 76.5% |

## Question changes

- Improved: 4 (q04, q08, q10, q13)
- Got worse: 3 (q02, q12, q14)
- Unchanged: 10 (q01, q03, q05, q06, q07, q09, q11, u01, u02, u03)

## q05 and the OCR document

- **Baseline** does not retrieve the OCR document. Retrieved pages: [8, 6, 5].
- **Expanded** does not retrieve the OCR document. Retrieved pages: [5, 8, 9].

## Questions whose top 3 changed

- **q02** worse. Expected pages [2]. Baseline pages [2, 1, 2]. Expanded pages [1, 2, 12].
- **q04** improved. Expected pages [3]. Baseline pages [9, 3, 3]. Expanded pages [3, 9, 3].
- **q08** improved. Expected pages [6]. Baseline pages [6, 11, 2]. Expanded pages [6, 11, 6].
- **q10** improved. Expected pages [8]. Baseline pages [8, 9, 7]. Expanded pages [8, 9, 8].
- **q12** worse. Expected pages [10]. Baseline pages [10, 9, 10]. Expanded pages [10, 9, 11].
- **q13** improved. Expected pages [5, 11]. Baseline pages [11, 5, 2]. Expanded pages [11, 5, 5].
- **q14** worse. Expected pages [12]. Baseline pages [11, 12, 9]. Expanded pages [11, 3, 3].

## Reading the result

Hit rate is higher with the baseline pool (92.9% vs 85.7%). Precision@3 is tied at 50.0%. Recall@3 is higher with the baseline pool (89.3% vs 82.1%). MRR is higher with the baseline pool (85.7% vs 82.1%). Unanswerable rejection is tied at 100.0%. Retrieval coverage is higher with the baseline pool (82.4% vs 76.5%).

Saved `gist_documents` count: 51 before, 51 after.
