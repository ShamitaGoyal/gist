"""Classify page-4 OCR boxes by where they sit on the page.

This is a layout experiment. It does not change PDF extraction or retrieval.

Run from the backend directory:

    python3 tests/test_ocr_layout.py
"""

from rapidocr import RapidOCR


IMAGE_PATH = "data/evaluation_results/page4.png"

# Rendered size of data/evaluation_results/page4.png.
IMAGE_WIDTH = 1836
IMAGE_HEIGHT = 2376

# Initial regions, expressed as fractions of that image.
HEADER_MAX_Y = 0.11 * IMAGE_HEIGHT
CAPTION_MIN_Y = 0.845 * IMAGE_HEIGHT
LINE_NUMBER_MAX_X = 0.115 * IMAGE_WIDTH
CODE_MAX_X = 0.43 * IMAGE_WIDTH
SECTION_HEADING_MAX_X = 0.58 * IMAGE_WIDTH
SECTION_HEADING_MIN_WIDTH = 0.08 * IMAGE_WIDTH
SECTION_HEADING_MAX_WIDTH = 0.16 * IMAGE_WIDTH

# Detections below this are still kept. The printout marks them.
LOW_CONFIDENCE = 0.80

CATEGORIES = ("code", "line_numbers", "explanations", "headings")


def box_width(box):
    xs = [point[0] for point in box]
    return max(xs) - min(xs)


def is_line_number(text, x_center):
    """Small numeric labels in the gutter at the left edge of the code."""

    if x_center >= LINE_NUMBER_MAX_X:
        return False
    return text.strip().isdigit()


def is_section_heading(text, x_center, width):
    """Section titles share the right column with the annotations.

    Their boxes are short and sit just left of the annotation paragraphs.
    Wrapped annotation lines are either narrower, farther right, or end
    with a period, so they stay in explanations.
    """

    if not (CODE_MAX_X <= x_center < SECTION_HEADING_MAX_X):
        return False
    if not (SECTION_HEADING_MIN_WIDTH <= width <= SECTION_HEADING_MAX_WIDTH):
        return False
    return not text.strip().endswith(".")


def classify(text, x_center, y_center, width):
    if y_center < HEADER_MAX_Y or y_center >= CAPTION_MIN_Y:
        return "headings"
    if is_section_heading(text, x_center, width):
        return "headings"
    if is_line_number(text, x_center):
        return "line_numbers"
    if x_center < CODE_MAX_X:
        return "code"
    return "explanations"


def detection_from_ocr(box, text, score):
    x_center = sum(point[0] for point in box) / 4
    y_center = sum(point[1] for point in box) / 4
    width = box_width(box)
    confidence = float(score)

    return {
        "text": text,
        "box": [[float(point[0]), float(point[1])] for point in box],
        "x": float(x_center),
        "y": float(y_center),
        "confidence": confidence,
        "low_confidence": confidence < LOW_CONFIDENCE,
        "category": classify(text, x_center, y_center, width),
    }


def print_category(name, items):
    title = name.replace("_", " ")
    print(f"\n=== {title.upper()} ({len(items)}) ===")

    if not items:
        print("(none)")
        return

    for item in items:
        flag = " [low confidence]" if item["low_confidence"] else ""
        print(
            f"X: {item['x']:7.1f} | "
            f"Y: {item['y']:7.1f} | "
            f"Confidence: {item['confidence']:.2f}{flag} | "
            f"Text: {item['text']}"
        )


def main():
    result = RapidOCR()(IMAGE_PATH)

    items = [
        detection_from_ocr(box, text, score)
        for box, text, score in zip(result.boxes, result.txts, result.scores)
    ]

    grouped = {category: [] for category in CATEGORIES}
    for item in items:
        grouped[item["category"]].append(item)

    for category in CATEGORIES:
        grouped[category].sort(key=lambda item: (item["y"], item["x"]))
        print_category(category, grouped[category])

    low_confidence = sum(1 for item in items if item["low_confidence"])
    print(
        f"\nClassified {len(items)} detections "
        f"({low_confidence} marked low confidence, none discarded)."
    )


if __name__ == "__main__":
    main()
