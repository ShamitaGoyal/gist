"""Add figure text that normal PDF extraction did not already capture.

The layout fractions come from the page-4 OCR experiment. Line numbers are
dropped. Code text is kept only as unverified OCR. Low-confidence text stays
marked instead of being corrected.
"""

import tempfile
from pathlib import Path

import pymupdf
from langchain_core.documents import Document
from rapidocr import RapidOCR


LOW_CONFIDENCE = 0.80
HEADER_MAX_Y = 0.11
CAPTION_MIN_Y = 0.845
LINE_NUMBER_MAX_X = 0.115
CODE_MAX_X = 0.43
SECTION_HEADING_MAX_X = 0.58
SECTION_HEADING_MIN_WIDTH = 0.08
SECTION_HEADING_MAX_WIDTH = 0.16
MIN_DRAWINGS_FOR_FIGURE = 50
MIN_NOVEL_CHARACTERS = 40
RENDER_ZOOM = 2


def supplement_figures(pdf_path, pages, document_id):
    """Return OCR chunks for figure pages, with chunk_index left unset."""

    text_by_page = {int(page["page_number"]): page["text"] for page in pages}
    document = pymupdf.open(pdf_path)
    engine = RapidOCR()
    supplements = []
    try:
        for page in document:
            page_number = page.number + 1
            if page_number not in text_by_page or not _worth_ocr(page):
                continue
            content = _novel_text(engine, page, text_by_page[page_number])
            if content is None:
                continue
            supplements.append(
                Document(
                    page_content=content,
                    metadata={
                        "document_id": document_id,
                        "page_number": page_number,
                        "section_headings": ["OCR figure"],
                        "chunking_strategy": "ocr_figure",
                        "source_type": "ocr_figure",
                    },
                )
            )
    finally:
        document.close()
    return supplements


def _worth_ocr(page):
    if page.get_images():
        return True
    return len(page.get_drawings()) >= MIN_DRAWINGS_FOR_FIGURE


def _novel_text(engine, page, page_text):
    with tempfile.TemporaryDirectory() as directory:
        image_path = Path(directory) / "page.png"
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(RENDER_ZOOM, RENDER_ZOOM))
        pixmap.save(image_path)
        result = engine(str(image_path))

    texts = result.txts or []
    if not texts:
        return None

    width = pixmap.width
    height = pixmap.height
    lines = []
    for box, text, score in zip(result.boxes, texts, result.scores):
        rendered = _render_line(box, text, score, width, height, page_text)
        if rendered:
            lines.append(rendered)
    if sum(len(line) for line in lines) < MIN_NOVEL_CHARACTERS:
        return None

    page_number = page.number + 1
    body = "\n".join(lines)
    return (
        f"Supplementary OCR for the figure on page {page_number}. "
        "Code transcribed by OCR is unverified.\n"
        f"{body}"
    )


def _render_line(box, text, score, width, height, page_text):
    cleaned = " ".join(str(text).split())
    if not cleaned or _is_line_number(cleaned, box, width):
        return None
    if _already_represented(cleaned, page_text):
        return None

    category = _classify(cleaned, box, width, height)
    if category == "line_numbers":
        return None
    if float(score) < LOW_CONFIDENCE:
        cleaned = f"[uncertain: {cleaned}]"
    if category == "code":
        cleaned = f"[unverified OCR code] {cleaned}"
    return cleaned


def _is_line_number(text, box, width):
    x_center = sum(point[0] for point in box) / 4
    return x_center < LINE_NUMBER_MAX_X * width and text.isdigit()


def _classify(text, box, width, height):
    x_center = sum(point[0] for point in box) / 4
    y_center = sum(point[1] for point in box) / 4
    box_width = max(point[0] for point in box) - min(point[0] for point in box)
    if y_center < HEADER_MAX_Y * height or y_center >= CAPTION_MIN_Y * height:
        return "headings"
    if (
        CODE_MAX_X * width <= x_center < SECTION_HEADING_MAX_X * width
        and SECTION_HEADING_MIN_WIDTH * width
        <= box_width
        <= SECTION_HEADING_MAX_WIDTH * width
        and not text.endswith(".")
    ):
        return "headings"
    if x_center < LINE_NUMBER_MAX_X * width and text.isdigit():
        return "line_numbers"
    if x_center < CODE_MAX_X * width:
        return "code"
    return "explanations"


def _already_represented(line, page_text):
    """True when the extracted page already contains this line as words."""

    normalized_line = " ".join(line.lower().split())
    normalized_page = " ".join(page_text.lower().split())
    return normalized_line in normalized_page
