"""Request and response shapes for document questions."""

from pydantic import BaseModel, Field, field_validator


class QuestionRequest(BaseModel):
    """A question about one uploaded document."""

    question: str = Field(
        description="Question to answer from that document only.",
        min_length=1,
        max_length=2000,
    )

    @field_validator("question")
    @classmethod
    def question_is_not_blank(cls, value):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty")
        return cleaned


class SourceCitation(BaseModel):
    """One retrieved chunk cited in the answer."""

    chunk_id: str = Field(description="Indexed chunk id, such as meridian_59.")
    document_id: str
    page_number: int | None = Field(description="PDF page number for this chunk.")
    source_type: str = Field(description="pdf_extraction or ocr_figure.")


class AnswerResponse(BaseModel):
    """Grounded answer for one document."""

    document_id: str
    question: str
    answer: str = Field(description="Answer text with citations appended by the server.")
    grounding_status: str = Field(
        description="grounded, partially_grounded, or insufficient_context."
    )
    sources: list[SourceCitation]
