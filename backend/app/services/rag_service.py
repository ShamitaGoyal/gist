from app.services.document_registry import DocumentNotFound, DocumentRegistry
from app.services.figure_retrieval import retrieve_for_document
from app.services.grounding import (
    INSUFFICIENT_MESSAGE,
    assess_grounding,
    attach_sources,
    source_from_chunk,
    strip_model_citations,
)
from app.services.hybrid_search import HybridSearchService
from app.services.llm_service import LLMService
from app.services.pdf_service import extract_pdf
from app.services.semantic_chunker import chunk_pages
from app.services.vector_store import VectorStore


class RAGService:
    def __init__(self, chunks=None, vector_store=None, registry=None, llm_service=None):
        self.llm_service = llm_service or LLMService()
        self.vector_store = vector_store
        self.registry = registry
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

    def answer_document(self, question, document_id, top_k=3):
        """Answer from chunks already indexed for one document."""

        vector_store = self.vector_store or VectorStore()
        registry = self.registry or DocumentRegistry("data/document_registry.json")
        try:
            record = registry.get_document(document_id)
        except DocumentNotFound as exc:
            raise ValueError(
                f"Document {document_id!r} has not been ingested."
            ) from exc
        if record["ingestion_status"] != "success":
            raise ValueError(
                f"Document {document_id!r} is not ready for questions. "
                f"Status: {record['ingestion_status']}. Error: {record['error']}"
            )

        chunks = vector_store.documents_for(document_id)
        if not chunks:
            raise ValueError(
                f"Document {document_id!r} has no indexed chunks."
            )

        retrieved = retrieve_for_document(
            question,
            chunks,
            document_id,
            vector_store.client,
            vector_store.collection.name,
            top_k=top_k,
        )
        return self._compose(
            question,
            retrieved["chunks"],
            retrieved["figure_retrieval_used"],
        )

    def answer_question(self, question, top_k=3):
        if self.hybrid_search is None:
            raise ValueError("Load a document before asking questions.")
        results = self.hybrid_search.search(question)[:top_k]
        return self._compose(question, results, figure_retrieval_used=False)

    def _compose(self, question, chunks, figure_retrieval_used):
        sources = [source_from_chunk(chunk) for chunk in chunks]
        if not chunks:
            return {
                "question": question,
                "answer": attach_sources(INSUFFICIENT_MESSAGE, []),
                "sources": [],
                "grounding_status": "insufficient_context",
                "figure_retrieval_used": figure_retrieval_used,
            }

        context = "\n\n".join(
            f"Chunk {source['chunk_id']}, page {source['page_number']}:\n"
            f"{chunk.page_content}"
            for chunk, source in zip(chunks, sources)
        )
        evidence = "\n".join(chunk.page_content for chunk in chunks)
        answer = strip_model_citations(
            self.llm_service.generate_answer(question, context)
        )
        return {
            "question": question,
            "answer": attach_sources(answer, sources),
            "sources": sources,
            "grounding_status": assess_grounding(answer, evidence),
            "figure_retrieval_used": figure_retrieval_used,
        }
