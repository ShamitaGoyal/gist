"""Add at most one figure-OCR chunk after the normal hybrid top 3.

The normal search keeps weights [0.5, 0.5] and candidate size 3. A second
search runs only when the question refers to a figure, diagram, image,
annotation, code example, or dotted visual mark. That second search is
limited to the requested document's ocr_figure chunks. RRF scores are not
used as confidence.
"""

from app.services.hybrid_search import HybridSearchService


_FIGURE_TERMS = (
    "figure",
    "diagram",
    "image",
    "illustration",
    "annotation",
    "screenshot",
    "visual",
    "dotted",
    "code example",
)


def question_needs_figure(question):
    folded = question.lower()
    return any(term in folded for term in _FIGURE_TERMS)


def chunk_identity(chunk):
    metadata = chunk.metadata
    return f"{metadata.get('document_id')}_{metadata.get('chunk_index')}"


def merge_ranked_chunks(primary, supplementary, document_id):
    """Keep the original ranking, then append one new OCR chunk if needed."""

    merged = []
    seen = set()
    for chunk in primary:
        if chunk.metadata.get("document_id") != document_id:
            continue
        identity = chunk_identity(chunk)
        if identity in seen:
            continue
        seen.add(identity)
        merged.append(chunk)
    for chunk in supplementary:
        if chunk.metadata.get("document_id") != document_id:
            continue
        if chunk.metadata.get("source_type") != "ocr_figure":
            continue
        identity = chunk_identity(chunk)
        if identity in seen:
            continue
        merged.append(chunk)
        break
    return merged


def retrieve_for_document(
    question,
    chunks,
    document_id,
    chroma_client,
    collection_name,
    top_k=3,
):
    primary_search = HybridSearchService(
        chunks,
        document_id=document_id,
        chroma_client=chroma_client,
        collection_name=collection_name,
    )
    primary = primary_search.search(question)[:top_k]
    if not question_needs_figure(question):
        return {"chunks": primary, "figure_retrieval_used": False}

    has_ocr = any(
        chunk.metadata.get("document_id") == document_id
        and chunk.metadata.get("source_type") == "ocr_figure"
        for chunk in chunks
    )
    if not has_ocr:
        return {"chunks": primary, "figure_retrieval_used": False}

    figure_search = HybridSearchService(
        chunks,
        document_id=document_id,
        source_type="ocr_figure",
        chroma_client=chroma_client,
        collection_name=collection_name,
    )
    supplementary = figure_search.search(question)[:top_k]
    return {
        "chunks": merge_ranked_chunks(primary, supplementary, document_id),
        "figure_retrieval_used": True,
    }
