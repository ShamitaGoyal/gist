import sys
from pathlib import Path

# Running this file directly puts tests/ on the path, not backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pdf_service import extract_pdf
from app.services.semantic_chunker import chunk_pages
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


# 1. Extract PDF text
pages = extract_pdf("data/pdf_files/meridian.pdf")

# 2. Create semantic chunks
chunks = chunk_pages(pages, document_id="meridian")

# 3. Generate embeddings
embedding_service = EmbeddingService()

texts = [chunk.page_content for chunk in chunks]
embeddings = embedding_service.embed_documents(texts)

# 4. Store chunks and embeddings in ChromaDB
vector_store = VectorStore()

stored_count = vector_store.add_documents(
    chunks,
    embeddings
)

# 5. Verify storage
print("=== CHROMADB STORAGE ===")
print("Chunks processed:", len(chunks))
print("Embeddings generated:", len(embeddings))
print("Chunks stored:", stored_count)
print("Total records in database:", vector_store.collection.count())

# 6. Inspect the first record in ChromaDB
results = vector_store.collection.get(
    limit=1,
    include=["documents", "metadatas", "embeddings"]
)

print("\n=== FIRST CHROMADB RECORD ===")

print("ID:")
print(results["ids"][0])

print("\nDOCUMENT TEXT:")
print(results["documents"][0])

print("\nMETADATA:")
print(results["metadatas"][0])

print("\nEMBEDDING DIMENSIONS:")
print(len(results["embeddings"][0]))

print("\nFIRST 5 EMBEDDING VALUES:")
print(results["embeddings"][0][:5])