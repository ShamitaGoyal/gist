"""Turn page-4 OCR boxes into structured Markdown.

Uses one RapidOCR pass and the classifier in test_ocr_layout.py.
Line numbers stay out of the code. Uncertain text is marked, not corrected.

Run from the backend directory:

    python3 tests/test_ocr_markdown.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_ocr_layout as layout


BACKEND_ROOT = Path(__file__).resolve().parents[1]
IMAGE_PATH = BACKEND_ROOT / "data" / "evaluation_results" / "page4.png"
OUTPUT_PATH = BACKEND_ROOT / "data" / "evaluation_results" / "page4_structured.md"

# Explanation lines in one paragraph sit about 24px apart.
# The next numbered note starts at least 50px lower.
PARAGRAPH_GAP = 40

# Diagram labels sit on the far right of the annotation column.
DIAGRAM_MIN_X = 0.70 * layout.IMAGE_WIDTH

# A section heading sits slightly below the first code line beside it.
CODE_HEADING_SLACK = 20

SECTION_START_NUMBERS = {
    "Data Binding Specification": 1,
    "View Specification": 7,
    "Malleability Specification": 13,
}


def by_position(item):
    return (item["y"], item["x"])


def render_text(item):
    """Keep the OCR string. Mark low-confidence text instead of fixing it."""

    text = item["text"].strip()
    if item["low_confidence"]:
        return f"[uncertain: {text}]"
    return text


def is_numeric_label(text):
    """Gutter numbers are already excluded. These are the circled callouts."""

    stripped = text.strip()
    if stripped.isdigit():
        return True
    return bool(stripped) and all(0x2460 <= ord(character) <= 0x2473 for character in stripped)


def heading_named(items, name):
    matches = [
        item
        for item in items
        if item["category"] == "headings" and item["text"].strip() == name
    ]
    if not matches:
        raise RuntimeError(f"OCR did not detect the heading {name!r}")
    return min(matches, key=by_position)


def lines_between(items, category, top, bottom):
    selected = [
        item
        for item in items
        if item["category"] == category and top <= item["y"] < bottom
    ]
    return sorted(selected, key=by_position)


def group_paragraphs(items):
    groups = []
    for item in items:
        if not groups or item["y"] - groups[-1][-1]["y"] > PARAGRAPH_GAP:
            groups.append([item])
        else:
            groups[-1].append(item)
    return groups


def join_group(group):
    return " ".join(render_text(item) for item in sorted(group, key=by_position))


def code_block(items):
    lines = [
        render_text(item)
        for item in items
        if not is_numeric_label(item["text"])
    ]
    if not lines:
        return "_No code text was detected in this section._"
    return "```text\n" + "\n".join(lines) + "\n```"


def explanation_lines(items, start_number):
    paragraphs = group_paragraphs(items)
    lines = []
    for offset, group in enumerate(paragraphs):
        number = start_number + offset
        lines.append(f"{number}. {join_group(group)}")
    if not lines:
        return ["_No explanation text was detected in this section._"]
    return lines


def diagram_lines(items):
    if not items:
        return []
    return [f"- {render_text(item)}" for item in items]


def split_annotations(items):
    prose = []
    diagrams = []
    for item in items:
        if item["x"] >= DIAGRAM_MIN_X:
            diagrams.append(item)
        else:
            prose.append(item)
    return prose, diagrams


def section_markdown(title, code_items, explanation_items):
    prose, diagrams = split_annotations(explanation_items)
    start_number = SECTION_START_NUMBERS[title]
    parts = [
        f"## {title}",
        "",
        "### Code",
        "",
        code_block(code_items),
        "",
        "### Explanations",
        "",
        "\n".join(explanation_lines(prose, start_number)),
    ]
    labels = diagram_lines(diagrams)
    if labels:
        parts.extend(["", "### Diagram labels", "", "\n".join(labels)])
    return "\n".join(parts)


def figure_caption(items):
    caption_items = [
        item
        for item in items
        if item["category"] == "headings" and item["y"] >= layout.CAPTION_MIN_Y
    ]
    caption_items.sort(key=by_position)
    if not caption_items:
        return "_No figure caption was detected._"
    return " ".join(render_text(item) for item in caption_items)


def build_markdown(items):
    view_heading = heading_named(items, "View Specification")
    malleability_heading = heading_named(items, "Malleability Specification")

    sections = [
        (
            "Data Binding Specification",
            layout.HEADER_MAX_Y,
            view_heading["y"] - CODE_HEADING_SLACK,
        ),
        (
            "View Specification",
            view_heading["y"] - CODE_HEADING_SLACK,
            malleability_heading["y"] - CODE_HEADING_SLACK,
        ),
        (
            "Malleability Specification",
            malleability_heading["y"] - CODE_HEADING_SLACK,
            layout.CAPTION_MIN_Y,
        ),
    ]

    parts = [
        "# Page 4",
        "",
        "## Figure Caption",
        "",
        figure_caption(items),
        "",
    ]
    for title, code_top, code_bottom in sections:
        explanation_top = code_top + CODE_HEADING_SLACK
        explanation_bottom = code_bottom + CODE_HEADING_SLACK
        if title == "Malleability Specification":
            explanation_bottom = layout.CAPTION_MIN_Y
        parts.append(
            section_markdown(
                title,
                lines_between(items, "code", code_top, code_bottom),
                lines_between(items, "explanations", explanation_top, explanation_bottom),
            )
        )
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def load_detections():
    """Run the same RapidOCR engine and classifier as test_ocr_layout.py."""

    result = layout.RapidOCR()(str(IMAGE_PATH))
    return [
        layout.detection_from_ocr(box, text, score)
        for box, text, score in zip(result.boxes, result.txts, result.scores)
    ]


def main():
    markdown = build_markdown(load_detections())
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
