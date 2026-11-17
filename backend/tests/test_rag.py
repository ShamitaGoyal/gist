import sys
from pathlib import Path

# Running this file directly puts tests/ on the path, not backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.rag_service import RAGService

rag = RAGService()

# Load the document and build retrieval indexes
chunk_count = rag.load_document(
    "data/pdf_files/meridian.pdf",
    document_id="meridian"
)

print("Chunks loaded:", chunk_count)

# Ask a question
question = "How does Meridian support end-user customization?"

result = rag.answer_question(question)

print("\n=== GIST HYBRID RAG RESPONSE ===")
print("\nQuestion:")
print(result["question"])

print("\nAnswer:")
print(result["answer"])

print("\nDetailed Sources:")
for source in result["sources"]:
    print(
        f"- Document: {source['document_id']}, "
        f"Page: {source['page_number']}, "
        f"Chunk: {source['chunk_id']}"
    )
    print(f"  Sections: {source['section_headings']}")
