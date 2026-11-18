"""Figure questions can add the page 4 OCR chunk without changing hybrid weights.

Run from the backend directory:

    python3 tests/test_figure_retrieval.py
"""

import sys
from pathlib import Path

import chromadb
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.embedding_service import EmbeddingService
from app.services.figure_retrieval import (
    merge_ranked_chunks,
    question_needs_figure,
    retrieve_for_document,
)
from app.services.vector_store import VectorStore


PREFIX_QUESTION = (
    "What does the dotted prefix in Meridian's data-binding specification indicate?"
)
ROLES_QUESTION = "How many default attribute roles does Meridian provide?"
OCR_TEXT = 'Reference values from data with the prefix ".".'


def chunk(document_id, index, page, text, source_type):
    return Document(
        page_content=text,
        metadata={
            "document_id": document_id,
            "chunk_index": index,
            "page_number": page,
            "source_type": source_type,
            "section_headings": ["Test"],
        },
    )


def test_merge_rules():
    assert question_needs_figure(PREFIX_QUESTION)
    assert question_needs_figure("What does Figure 3 show?")
    assert not question_needs_figure(ROLES_QUESTION)

    pdf = chunk("meridian", 1, 3, "Data binding maps attributes.", "pdf_extraction")
    ocr = chunk("meridian", 9, 4, OCR_TEXT, "ocr_figure")
    other = chunk("other_paper", 0, 4, "Other figure secret.", "ocr_figure")
    duplicate = chunk("meridian", 9, 4, OCR_TEXT, "ocr_figure")

    merged = merge_ranked_chunks([pdf], [other, ocr], "meridian")
    assert [item.metadata["chunk_index"] for item in merged] == [1, 9]
    assert all(item.metadata["document_id"] == "meridian" for item in merged)

    again = merge_ranked_chunks([pdf, ocr], [duplicate], "meridian")
    assert [item.metadata["chunk_index"] for item in again] == [1, 9]
    print("Merge keeps ranking, drops other documents, and removes duplicates.")


def test_page4_ocr_retrieval():
    pdf_chunks = [
        chunk("meridian", 0, 5, "Meridian provides twelve default attribute roles.", "pdf_extraction"),
        chunk("meridian", 1, 6, "Semantic zoom changes shown attributes during scroll.", "pdf_extraction"),
        chunk("meridian", 2, 10, "The website builder spreads overview types into a grid.", "pdf_extraction"),
        chunk("meridian", 3, 9, "A workaround stores the first offer in a separate attribute.", "pdf_extraction"),
    ]
    ocr = chunk("meridian", 4, 4, OCR_TEXT, "ocr_figure")
    other = chunk("other_paper", 0, 4, "Other figure secret about a dotted badge.", "ocr_figure")
    documents = pdf_chunks + [ocr, other]

    store = VectorStore(
        client=chromadb.EphemeralClient(),
        collection_name="figure_retrieval_test",
    )
    embeddings = EmbeddingService().embed_documents(
        [item.page_content for item in documents]
    )
    store.add_documents(documents, embeddings)

    figure = retrieve_for_document(
        PREFIX_QUESTION,
        documents,
        "meridian",
        store.client,
        store.collection.name,
    )
    assert figure["figure_retrieval_used"]
    identities = [
        f"{item.metadata['document_id']}_{item.metadata['chunk_index']}"
        for item in figure["chunks"]
    ]
    assert "meridian_4" in identities
    assert "other_paper_0" not in identities
    assert all(item.metadata["document_id"] == "meridian" for item in figure["chunks"])
    ocr_hit = next(item for item in figure["chunks"] if item.metadata["chunk_index"] == 4)
    assert ocr_hit.metadata["source_type"] == "ocr_figure"
    assert ocr_hit.metadata["page_number"] == 4

    roles = retrieve_for_document(
        ROLES_QUESTION,
        documents,
        "meridian",
        store.client,
        store.collection.name,
    )
    assert roles["figure_retrieval_used"] is False
    print("Figure question retrieved meridian_4. The roles question did not add OCR.")
    print(f"Figure chunk ids: {identities}")


def main():
    test_merge_rules()
    test_page4_ocr_retrieval()
    print("Passed.")


if __name__ == "__main__":
    main()
