
from app.services.pdf_service import extract_pdf
from app.services.semantic_chunker import chunk_pages
from app.services.hybrid_search import HybridSearchService
from app.services.llm_service import LLMService


class RAGService:
    def __init__(self, chunks=None):
        self.llm_service = LLMService()
        self.hybrid_search = None

        if chunks is not None:
            self.hybrid_search = HybridSearchService(chunks)

    def load_document(self, pdf_path, document_id):
        # 1. Extract text from the PDF
        pages = extract_pdf(pdf_path)

        # 2. Create semantic chunks
        chunks = chunk_pages(pages, document_id=document_id)

        # 3. Initialize hybrid search with those chunks
        self.hybrid_search = HybridSearchService(chunks)

        return len(chunks)

    def answer_question(self, question, top_k=3):
        if self.hybrid_search is None:
            raise ValueError("Load a document before asking questions.")

        # 4. Retrieve relevant chunks using hybrid search
        results = self.hybrid_search.search(question)

        # 5. Limit the results passed to the LLM
        results = results[:top_k]

        if not results:
            return {
                "question": question,
                "answer": "I couldn't find sufficiently relevant information in the document to answer this question.",
                "sources": []
            }

        context_parts = []
        sources = []

        for chunk in results:
            metadata = chunk.metadata
            chunk_id = (
                f"{metadata['document_id']}_"
                f"{metadata['chunk_index']}"
            )

            context_parts.append(
                f"[Source: {metadata['document_id']}, "
                f"Page: {metadata['page_number']}, "
                f"Chunk: {chunk_id}]\n"
                f"{chunk.page_content}"
            )

            sources.append({
                "chunk_id": chunk_id,
                "document_id": metadata["document_id"],
                "page_number": metadata["page_number"],
                "section_headings": metadata["section_headings"]
            })

        context = "\n\n".join(context_parts)

        # 6. Generate an answer using the retrieved context
        answer = self.llm_service.generate_answer(question, context)

        formatted_answer = answer + "\n\nSources:\n"

        for i, source in enumerate(sources, start=1):
            formatted_answer += (
                f"[{i}] {source['document_id']} "
                f"- Page {source['page_number']}\n"
            )

        return {
            "question": question,
            "answer": formatted_answer,
            "sources": sources
        }
