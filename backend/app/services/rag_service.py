from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.llm_service import LLMService


class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.llm_service = LLMService()

    def answer_question(self, question, top_k=3):

        # 1. Convert the user's question into an embedding
        query_embedding = self.embedding_service.embed_query(question)

        # 2. Search ChromaDB for the most relevant chunks
        results = self.vector_store.search(
            query_embedding,
            top_k=top_k
        )

        # 3. Prepare the retrieved text and source information
        context_parts = []
        sources = []

        for i in range(len(results["ids"][0])):

            document_text = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            chunk_id = results["ids"][0][i]

            context_parts.append(
                f"Source: {metadata['document_id']}, "
                f"Page: {metadata['page_number']}\n"
                f"{document_text}"
            )

            sources.append({
                "chunk_id": chunk_id,
                "document_id": metadata["document_id"],
                "page_number": metadata["page_number"],
                "section_headings": metadata["section_headings"],
                "distance": results["distances"][0][i]
            })

        # 4. Combine retrieved chunks into one context string
        context = "\n\n".join(context_parts)

        # 5. Ask the LLM to answer using the retrieved context
        answer = self.llm_service.generate_answer(
            question=question,
            context=context
        )

        # 6. Return the answer and its sources
        return {
            "question": question,
            "answer": answer,
            "sources": sources
        }