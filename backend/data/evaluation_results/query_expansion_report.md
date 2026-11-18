# Query expansion evaluation

Generated: 2026-11-18T06:32:53+00:00
Dataset: `meridian-retrieval-v1`

## Setup

Both configurations search one frozen corpus. The expanded run retrieves with the rewritten query. Relevance labels stay on the original question.

- PDF chunks: 52
- OCR documents: 1
- BM25 candidate k: 10
- Semantic candidate k: 10
- Final results kept: 3
- RRF weights: 0.5 / 0.5, c=60
- Acceptance gate: squared L2 distance <= 0.75 against the query that was searched
- Expansion model: `llama3.2:1b` at temperature 0.0

Hit rate, precision, recall, and MRR use the fused top 3 before the distance gate. Rejection rate and coverage use the distance gate. A chunk is relevant when its page is one of the original question's expected pages.

A question improves when query expansion is better on the first metric that differs. For answerable questions that order is hit, reciprocal rank, precision, then recall. For unanswerable questions, correctly rejecting the question is better than accepting a chunk.

## Aggregate comparison

| Metric | Original question | Query expansion |
| --- | ---: | ---: |
| Hit Rate | 85.7% | 92.9% |
| Precision@3 | 50.0% | 45.2% |
| Recall@3 | 82.1% | 89.3% |
| MRR | 82.1% | 81.0% |
| Unanswerable rejection rate | 100.0% | 66.7% |
| Retrieval coverage | 76.5% | 70.6% |

## Question changes

- Improved: 1 (q14)
- Got worse: 5 (q07, q08, q11, q13, u03)
- Unchanged: 11 (q01, q02, q03, q04, q05, q06, q09, q10, q12, u01, u02)

## q05 and the OCR document

- **Original question** does not retrieve the OCR document. Retrieved pages: [5, 8, 9].
- **Query expansion** does not retrieve the OCR document. Retrieved pages: [3, 3, 5].
- Expanded query: "Attribute value prefixes referencing field data specifications"

## Per-question results

| Question | Change | Original pages | Expansion pages | Expanded query |
| --- | --- | --- | --- | --- |
| q01 | unchanged | 1, 3, 2 | 1, 2, 6 | "Overview-detail interface (ODI) search query" |
| q02 | unchanged | 1, 2, 12 | 1, 2, 12 | "Design dimensions of overview-detail interfaces identified by Min et al." |
| q03 | unchanged | 3, 3, 9 | 3, 3, 9 | "what do openIn, openFrom, and openBy properties specify for a meridian detail view in a document retrieval system" |
| q04 | unchanged | 3, 9, 3 | 3, 11, 3 | "Meridian's data binding approach differs from Angular and React, as it separates data binding from view rendering, aligning with principles of separation of concerns and modularity in software development." |
| q05 | unchanged | 5, 8, 9 | 3, 3, 5 | "Attribute value prefixes referencing field data specifications" |
| q06 | unchanged | 5, 3, 9 | 5, 3, 9 | "How many default attribute roles does Meridian provide?" |
| q07 | worse | 6, 6, 6 | 6, 6, 11 | "How does Meridian implement semantic zooming when a user scrolls or pinches, and what are the underlying technologies used to achieve this feature?" |
| q08 | worse | 6, 11, 6 | 6, 3, 5 | "What is the layout of items arranged in a horizontal row with one item moved to the right of another?" |
| q09 | unchanged | 7, 1, 12 | 7, 1, 8 | "Which three real-world overview-detail interfaces did the developer package reproduce?" |
| q10 | unchanged | 8, 9, 8 | 8, 9, 8 | "How does the recursive thesaurus specification enable the creation of nested and hierarchical relationships between the overview and detail view in a document retrieval system?" |
| q11 | worse | 9, 9, 6 | 8, 9, 9 | "how to retrieve only the first item in a list when displaying a smartphone detail view" |
| q12 | unchanged | 10, 9, 11 | 10, 3, 9 | "what does the website builder do when a designer clicks on the overview type property in design space?" |
| q13 | worse | 11, 5, 5 | 11, 5, 10 | "How can end-users customize website content, such as adding calorie information, and compare this customization with data sorting and filtering in a document retrieval system?" |
| q14 | improved | 11, 3, 3 | 1, 11, 12 | "Where does the paper locate Meridian in the context of website development tools, specifically Figma, Wix, Material-UI, and Bootstrap?" |
| u01 | unchanged | 11, 14, 10 | 4, 14, 9 | "Authors' preferred culinary preference" |
| u02 | unchanged | 10, 6, 2 | 6, 14, 11 | I can't help with that. |
| u03 | worse | 11, 3, 5 | 11, 3, 5 | "How many participants completed the controlled lab study of the Meridian website builder?" |

## Reading the result

Hit rate is higher with query expansion (92.9% vs 85.7%). Precision@3 is higher with the original question (50.0% vs 45.2%). Recall@3 is higher with query expansion (89.3% vs 82.1%). MRR is higher with the original question (82.1% vs 81.0%). Unanswerable rejection is higher with the original question (100.0% vs 66.7%). Retrieval coverage is higher with the original question (76.5% vs 70.6%).

Saved `gist_documents` count: 51 before, 51 after.
