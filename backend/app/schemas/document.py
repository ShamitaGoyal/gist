"""Request and response shapes for the document library."""

from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    """A document shown in the library list."""

    document_id: str = Field(description="Stable id used by the API.")
    filename: str = Field(description="Original uploaded filename, with unsafe characters removed.")
    ingestion_status: str = Field(description="success or failed.")
    total_pages: int = Field(description="Pages extracted from the PDF.")
    total_chunks: int = Field(description="Indexed chunks, including any figure OCR chunks.")
    created_at: str = Field(description="UTC time of the first ingestion attempt.")
    last_ingestion_at: str = Field(description="UTC time of the latest ingestion attempt.")


class DocumentDetail(DocumentSummary):
    """Full status for one document. Storage paths are not included."""

    total_embeddings: int = Field(description="Embeddings stored for this document.")
    error: str | None = Field(description="Public ingestion error, if the latest attempt failed.")


class DeleteDocumentResponse(BaseModel):
    """Confirmation that one document was removed."""

    document_id: str
    deleted: bool = True
