import sys
from pathlib import Path

# Running this file directly puts tests/ on the path, not backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


# 1. Initialize services
embedding_service = EmbeddingService()
vector_store = VectorStore()


# 2. Write a question
query = "How does Meridian help users interact with interfaces?"


# 3. Convert the question into an embedding
query_embedding = embedding_service.embed_query(query)


# 4. Search ChromaDB
results = vector_store.search(
    query_embedding=query_embedding,
    top_k=3
)


# 5. Display the results
print("\n=== SEARCH RESULTS ===")
print("Question:", query)

for i in range(len(results["ids"][0])):
    print(f"\n--- Result {i + 1} ---")

    print("Chunk ID:", results["ids"][0][i])
    print("Distance:", results["distances"][0][i])
    print("Metadata:", results["metadatas"][0][i])
    print("Text:", results["documents"][0][i])