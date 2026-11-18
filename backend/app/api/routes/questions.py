"""Ask a question about one ingested document."""

import logging

from fastapi import APIRouter

from app.api.dependencies import ContainerDep
from app.api.errors import APIError
from app.schemas.question import AnswerResponse, QuestionRequest, SourceCitation
from app.services.llm_providers import GeminiLimitError


logger = logging.getLogger("gist.api")
router = APIRouter(prefix="/api/documents", tags=["questions"])


@router.post("/{document_id}/ask", response_model=AnswerResponse)
def ask_question(document_id: str, body: QuestionRequest, container: ContainerDep):
    """Answer from the requested document using the existing RAG service."""

    try:
        result = container.rag.answer_document(body.question, document_id)
    except ValueError as exc:
        message = str(exc)
        logger.info("Question rejected for %s: %s", document_id, message)
        if "not been ingested" in message:
            raise APIError(404, "Document not found.") from None
        if "not ready" in message:
            raise APIError(
                409,
                "Document ingestion has not completed successfully.",
            ) from None
        raise APIError(400, "The question could not be answered.") from None
    except GeminiLimitError:
        logger.info("Local Gemini limit rejected a question for %s", document_id)
        raise APIError(429, "The local Gemini request limit was reached.") from None
    except Exception:
        logger.exception("Answer generation failed for %s", document_id)
        raise APIError(500, "Answer generation failed.") from None

    return AnswerResponse(
        document_id=document_id,
        question=result["question"],
        answer=result["answer"],
        grounding_status=result["grounding_status"],
        sources=[
            SourceCitation(
                chunk_id=source["chunk_id"],
                document_id=source["document_id"],
                page_number=source.get("page_number"),
                source_type=source.get("source_type", "pdf_extraction"),
            )
            for source in result["sources"]
        ],
    )
