# Task: Build a Retrieval Evaluation Framework for Gist (Semantic Search vs. Hybrid Search)

I want to build a comprehensive but lightweight evaluation framework for my RAG application, Gist.

The goal is to objectively compare my existing semantic-only retrieval system against my new hybrid retrieval system (BM25 + ChromaDB + Reciprocal Rank Fusion).

Do not rebuild my existing retrieval architecture. Reuse the existing services, functions, data, and project structure wherever possible.

## 1. Current project architecture

Backend structure:

backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── services/
│       ├── pdf_service.py
│       ├── semantic_chunker.py
│       ├── embedding_service.py
│       ├── vector_store.py
│       ├── bm25_service.py
│       ├── hybrid_search.py
│       ├── llm_service.py
│       └── rag_service.py
├── data/
│   ├── pdf_files/
│   │   └── meridian.pdf
│   └── chroma_db/
└── tests/
    ├── test_embeddings.py
    ├── test_vector_store.py
    ├── test_search.py
    ├── test_bm25.py
    ├── test_hybrid_search.py
    ├── test_rag.py
    └── test_retrieval_evaluation.py

Existing technologies:
- Python
- LangChain
- Ollama
- nomic-embed-text for embeddings
- ChromaDB for persistent vector storage
- rank-bm25 for keyword retrieval
- langchain-classic EnsembleRetriever for RRF
- Llama 3.2 1B for answer generation

## 2. Existing retrieval implementations

### Semantic-only retrieval

The existing VectorStore service uses ChromaDB.

It has a search method that accepts:
- query_embedding
- top_k
- max_distance

It returns:
- ids
- documents
- metadatas
- distances

The existing embedding service provides:
- embed_documents(texts)
- embed_query(query)

### BM25 retrieval

The existing BM25Service accepts document chunks and builds a BM25Retriever.

### Hybrid retrieval

The existing HybridSearchService:
- Builds a BM25Retriever from the document chunks.
- Connects to the existing ChromaDB collection named gist_documents.
- Uses OllamaEmbeddings with nomic-embed-text.
- Creates a semantic retriever with k=3.
- Combines BM25 and semantic retrieval through EnsembleRetriever.
- Uses weights=[0.5, 0.5].
- Exposes search(query), returning LangChain Document objects.

Important: Inspect the actual implementations before coding. Do not assume the descriptions above are perfectly aligned with the current files. Preserve existing APIs unless a change is necessary.

## 3. Evaluation dataset

Create a manually labeled evaluation dataset with at least 12 questions based on the actual content of meridian.pdf.

Use a mixture of question types:

- Direct factual questions.
- Questions about exact technical terminology.
- Questions about relationships between concepts.
- Questions about specific Meridian features.
- Questions that require information from different sections.
- Unanswerable questions that the PDF does not contain enough information to answer.

For each question, store:

- question_id
- question
- expected_pages: list of relevant page numbers
- answerable: boolean
- question_type
- optional notes explaining why the page is relevant

Important:
- Inspect the actual extracted PDF content before creating the dataset.
- Do not invent facts or page numbers.
- Manually label expected pages based on the actual document.
- Include at least 3 unanswerable questions.
- Make sure the questions cover multiple pages rather than repeatedly testing the same section.
- Keep the evaluation dataset separate from the retrieval implementation.

Put the dataset in:

backend/data/evaluation_questions.json

## 4. Retrieval systems to compare

Run both retrieval methods against exactly the same questions.

System A: Semantic-only
- Use the existing EmbeddingService and VectorStore.
- Generate query embeddings.
- Retrieve the top 3 chunks from ChromaDB.
- Preserve the current distance filtering behavior where appropriate.
- Make the distance threshold configurable.

System B: Hybrid
- Use the existing HybridSearchService.
- Retrieve the top 3 chunks using BM25 + semantic search + RRF.
- Use the same underlying document and chunk dataset.
- Do not apply the semantic ChromaDB distance threshold to RRF scores. They are not comparable.

Both systems must receive identical questions and use the same top_k value.

## 5. Metrics to calculate

Calculate the following metrics separately for semantic-only and hybrid retrieval.

### A. Hit Rate

Question: Did the system retrieve at least one chunk from an expected page?

Formula:

Hit Rate = Number of answerable questions with at least one relevant page retrieved / Total answerable questions

Report as a percentage.

### B. Precision@3

Measure how many of the top 3 retrieved chunks are relevant.

A chunk is relevant if its page_number is included in expected_pages.

Formula:

Precision@3 = Relevant retrieved chunks / Total retrieved chunks, using a maximum of 3 per question.

Report the average across answerable questions.

### C. Recall@3

Measure whether the system retrieved the expected relevant pages.

For each question:

Recall@3 = Number of distinct expected pages retrieved / Number of expected pages

Report the average across answerable questions.

### D. Mean Reciprocal Rank (MRR)

Measure how high the first relevant chunk appears.

For each question:
- If the first relevant chunk is rank 1, reciprocal rank = 1.
- If rank 2, reciprocal rank = 1/2.
- If rank 3, reciprocal rank = 1/3.
- If no relevant chunk is retrieved, reciprocal rank = 0.

Average across answerable questions.

### E. Unanswerable Rejection Rate

For unanswerable questions, measure how often the system correctly retrieves no sufficiently relevant chunks.

For semantic-only:
- Use the configurable ChromaDB distance threshold.

For hybrid:
- Do not treat RRF rankings as confidence scores.
- Implement a separate, configurable rejection mechanism.
- Consider a conservative keyword/semantic relevance check or another explainable approach.
- Do not invent a threshold without evaluating it.
- Clearly document that this is a preliminary rejection mechanism.

Formula:

Rejection Rate = Number of unanswerable questions with no accepted results / Total unanswerable questions

### F. Retrieval Coverage

Report the percentage of all questions for which the system returned at least one accepted chunk.

Keep this separate from answerable-question Hit Rate.

## 6. Charts and visualizations

Generate clear, readable charts using matplotlib.

Save charts in:

backend/data/evaluation_results/

Required charts:

1. **Metric Comparison Chart**
   - Grouped bar chart.
   - Compare semantic-only vs hybrid for:
     - Hit Rate
     - Precision@3
     - Recall@3
     - MRR
     - Unanswerable Rejection Rate
   - Show percentages or decimals clearly.
   - Label each bar with its value.

2. **Question-Level Hit Rate Chart**
   - Show each answerable question.
   - Compare whether semantic-only and hybrid retrieved at least one expected page.
   - Use readable question IDs rather than long question text.

3. **Precision@3 Comparison**
   - Compare semantic-only and hybrid precision for each question.
   - Clearly identify questions where hybrid improves or performs worse.

4. **Rejection Rate Chart**
   - Show how each system handled the unanswerable questions.
   - Distinguish correctly rejected questions from incorrectly accepted ones.

5. **Retrieval Latency Chart**
   - Compare average retrieval time per question for semantic-only and hybrid.
   - Measure retrieval only, excluding PDF extraction, chunking, and LLM generation.
   - Run multiple repetitions if practical and report the average.

Use matplotlib only. Do not use seaborn.

## 7. Detailed evaluation output

Save a JSON file:

backend/data/evaluation_results/evaluation_results.json

Include:
- Evaluation timestamp.
- Dataset version or identifier.
- Number of answerable questions.
- Number of unanswerable questions.
- Configuration values (top_k, distance threshold, RRF weights, etc.).
- Aggregate metrics for both retrieval systems.
- Per-question results for both systems.
- Retrieved page numbers.
- Retrieved chunk IDs.
- Relevance judgments.
- Retrieval latency.
- Any rejected results and rejection reasons.

Also generate:

backend/data/evaluation_results/evaluation_report.md

The Markdown report should explain:
- What was evaluated.
- How the metrics are calculated.
- The aggregate comparison.
- Important per-question differences.
- Which questions each system struggled with.
- Whether hybrid retrieval improved over semantic-only retrieval.
- Limitations of the small evaluation dataset.
- Recommended next improvements.

Do not claim one system is better unless the measured results support that conclusion.

## 8. Suggested code organization

Use a clean structure such as:

backend/
├── app/
│   └── services/
│       └── retrieval_evaluator.py
├── data/
│   ├── evaluation_questions.json
│   └── evaluation_results/
└── tests/
    └── run_retrieval_evaluation.py

You may adjust this structure if the existing project suggests a cleaner design.

Keep the evaluation logic separate from production RAG code.

Avoid unnecessary dependencies. Reuse matplotlib and existing installed packages where possible.

## 9. Execution

Create a single runnable evaluation script.

I should be able to run:

python3 tests/run_retrieval_evaluation.py

It should:
1. Load the PDF and evaluation dataset.
2. Extract and chunk the PDF only once.
3. Initialize both retrieval systems.
4. Run the same questions through both systems.
5. Calculate metrics.
6. Generate charts.
7. Save JSON results.
8. Generate a Markdown report.
9. Print a concise terminal summary.

Do not call the LLM for this evaluation. We are evaluating retrieval quality, not answer generation quality.

## 10. Important engineering requirements

- Inspect existing source files before editing.
- Do not overwrite working retrieval services unnecessarily.
- Avoid duplicate embedding generation when possible.
- Use consistent document IDs and chunk IDs.
- Ensure both systems evaluate the same chunks.
- Make file paths robust when running from backend/.
- Handle empty retrieval results safely.
- Handle missing expected pages safely.
- Make random or nondeterministic behavior explicit.
- Add useful comments and docstrings.
- Do not hardcode evaluation metrics or fabricate results.
- Do not silently skip failed questions.
- Include error messages that identify the question and retrieval system.
- Ensure all output directories are created automatically.
- Keep the code understandable for a beginner learning RAG.

## 11. Final validation

After implementing everything:

1. Run the evaluation script.
2. Fix any errors.
3. Confirm that both retrieval systems run on the same dataset.
4. Confirm that all charts are generated.
5. Confirm that the JSON and Markdown report are saved.
6. Print the final aggregate metrics in the terminal.

At the end, provide me with:
- Files created or modified.
- The command to run the evaluation.
- A short explanation of each metric.
- The paths to the generated charts and report.
- Any assumptions or limitations in the implementation.

Most importantly: I want real, reproducible evaluation results based on the actual Meridian PDF, not example numbers or fabricated charts.