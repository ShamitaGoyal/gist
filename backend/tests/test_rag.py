import sys
from pathlib import Path

# Running this file directly puts tests/ on the path, not backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.rag_service import RAGService

rag = RAGService()

question = "How does Meridian support end-user customization?"

result = rag.answer_question(question)

print("\n=== GIST RAG RESPONSE ===")

print("\nQuestion:")
print(result["question"])

print("\nAnswer:")
print(result["answer"])

print("\nSources:")

for source in result["sources"]:
    print(
        f"- Document: {source['document_id']}, "
        f"Page: {source['page_number']}, "
        f"Chunk: {source['chunk_id']}"
    )

    print(f"  Sections: {source['section_headings']}")
    print(f"  Distance: {source['distance']:.4f}")