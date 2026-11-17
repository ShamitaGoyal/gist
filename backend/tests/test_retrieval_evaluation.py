import sys
from pathlib import Path

# Running this file directly puts tests/ on the path, not backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


embedding_service = EmbeddingService()
vector_store = VectorStore()


# Questions with manually identified relevant pages
test_cases = [
    {
        "question": "How does Meridian support end-user customization?",
        "expected_pages": [11],
        "answerable": True
    },
    {
        "question": "What does the Meridian specification define about views and data binding?",
        "expected_pages": [3],
        "answerable": True
    },
    {
        "question": "What real-world examples does Meridian reproduce?",
        "expected_pages": [7],
        "answerable": True
    },
    {
        "question": "What is the authors' favorite food?",
        "expected_pages": [],
        "answerable": False
    }
]


# Experiment with different distance thresholds
thresholds = [0.65, 0.75, 0.85]


for threshold in thresholds:

    print(f"\n{'=' * 50}")
    print(f"TESTING THRESHOLD: {threshold}")
    print(f"{'=' * 50}")

    relevant_hits = 0
    answerable_questions = 0
    correct_rejections = 0
    unanswerable_questions = 0

    for test in test_cases:

        question = test["question"]

        # Convert question into an embedding
        query_embedding = embedding_service.embed_query(question)

        # Retrieve chunks using the current threshold
        results = vector_store.search(
            query_embedding,
            top_k=3,
            max_distance=threshold
        )

        retrieved_pages = [
            metadata["page_number"]
            for metadata in results["metadatas"][0]
        ]

        print(f"\nQuestion: {question}")
        print(f"Retrieved pages: {retrieved_pages}")

        if test["answerable"]:

            answerable_questions += 1

            expected_pages = test["expected_pages"]

            if any(page in retrieved_pages for page in expected_pages):
                relevant_hits += 1
                print("Result: PASS - Found an expected page")
            else:
                print("Result: FAIL - Expected page not retrieved")

        else:

            unanswerable_questions += 1

            if len(retrieved_pages) == 0:
                correct_rejections += 1
                print("Result: PASS - Correctly rejected")
            else:
                print("Result: FAIL - Retrieved potentially irrelevant chunks")

    # Calculate evaluation metrics
    hit_rate = relevant_hits / answerable_questions
    rejection_rate = correct_rejections / unanswerable_questions

    print("\n--- EVALUATION SUMMARY ---")
    print(f"Relevant retrieval hit rate: {hit_rate:.0%}")
    print(f"Unanswerable rejection rate: {rejection_rate:.0%}")