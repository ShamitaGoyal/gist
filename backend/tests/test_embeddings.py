
import sys
from pathlib import Path

# Running this file directly puts tests/ on the path, not backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.embedding_service import EmbeddingService


# create our embedding service
service = EmbeddingService()


# test 1: embed a user question
query = "What is an ODI?"

embedding = service.embed_query(query)

print("=== QUERY EMBEDDING ===")
print("Question:", query)
print("Vector dimensions:", len(embedding))
print("First 5 values:", embedding[:5])


# test 2: embed multiple document chunks
texts = [
    "an overview of multiple items alongside a detailed view of a selected item",
    "a view of a single item with detailed information and context"
]

document_embeddings = service.embed_documents(texts)

print("\n=== DOCUMENT EMBEDDINGS ===")
print("Number of chunks:", len(document_embeddings))
print("Dimensions per vector:", len(document_embeddings[0]))
print("First 5 values of chunk 1:", document_embeddings[0][:5])
