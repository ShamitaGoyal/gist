"""Draw the page-4 layout categories on the original image.

Uses the classifier in test_ocr_layout.py. This does not change PDF
extraction or retrieval.

Run from the backend directory:

    python3 tests/visualize_ocr_layout.py
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_ocr_layout as layout


BACKEND_ROOT = Path(__file__).resolve().parents[1]
IMAGE_PATH = BACKEND_ROOT / "data" / "evaluation_results" / "page4.png"
OUTPUT_PATH = BACKEND_ROOT / "data" / "evaluation_results" / "page4_annotated.png"

COLORS = {
    "code": (29, 78, 216),
    "line_numbers": (194, 65, 12),
    "explanations": (21, 128, 61),
    "headings": (124, 58, 237),
}
LOW_CONFIDENCE_COLOR = (202, 138, 4)

CATEGORY_LABELS = {
    "code": "Code",
    "line_numbers": "Line numbers",
    "explanations": "Explanations",
    "headings": "Headings/captions",
}


def load_font(size):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def polygon(box):
    return [(point[0], point[1]) for point in box]


def text_size(draw, text, font):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def label_for(item):
    """Repeat OCR text only where a second line will not cover the page.

    Dense code and annotation lines are about 24 pixels apart, so a label
    above each one hides the line above it. Low-confidence text is the
    exception: that string is what we need to inspect, so it is always labeled.
    """

    if item["low_confidence"]:
        return "* " + item["text"].replace("\n", " ").strip()
    if item["category"] != "headings":
        return None
    if item["y"] < layout.HEADER_MAX_Y or item["y"] >= layout.CAPTION_MIN_Y:
        return None

    text = item["text"].replace("\n", " ").strip()
    if len(text) > 42:
        text = text[:41] + "…"
    return text


def draw_box(draw, item):
    points = polygon(item["box"])
    color = COLORS[item["category"]]
    fill = color + (48,)

    draw.polygon(points, fill=fill)
    if item["low_confidence"]:
        draw.line(points + [points[0]], fill=LOW_CONFIDENCE_COLOR + (255,), width=5)
    draw.line(points + [points[0]], fill=color + (255,), width=2)


def draw_label(draw, item, font):
    label = label_for(item)
    if label is None:
        return

    points = polygon(item["box"])
    color = LOW_CONFIDENCE_COLOR if item["low_confidence"] else COLORS[item["category"]]
    label_width, label_height = text_size(draw, label, font)
    x = min(point[0] for point in points)
    y = min(point[1] for point in points) - label_height - 3
    if item["low_confidence"]:
        x = max(point[0] for point in points) + 4
        y = min(point[1] for point in points)
    if y < 0:
        y = 0

    draw.rectangle(
        [x, y, x + label_width + 4, y + label_height + 2],
        fill=(255, 255, 255, 230),
    )
    draw.text((x + 2, y + 1), label, fill=color + (255,), font=font)


def draw_legend(draw, font, image_width):
    x = 12
    y = 8
    swatch = 16
    for category in layout.CATEGORIES:
        label = CATEGORY_LABELS[category]
        draw.rectangle(
            [x, y, x + swatch, y + swatch],
            fill=COLORS[category] + (255,),
        )
        draw.text((x + swatch + 6, y), label, fill=(17, 17, 17, 255), font=font)
        text_width, _ = text_size(draw, label, font)
        x += swatch + 12 + text_width + 16

    note = "* yellow ring = low confidence"
    note_width, _ = text_size(draw, note, font)
    draw.text(
        (image_width - note_width - 12, 8),
        note,
        fill=LOW_CONFIDENCE_COLOR + (255,),
        font=font,
    )


def main():
    result = layout.RapidOCR()(str(IMAGE_PATH))
    items = [
        layout.detection_from_ocr(box, text, score)
        for box, text, score in zip(result.boxes, result.txts, result.scores)
    ]

    image = Image.open(IMAGE_PATH).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(13)

    for item in items:
        draw_box(draw, item)
    for item in items:
        draw_label(draw, item, font)
    draw_legend(draw, font, image.width)

    image = Image.alpha_composite(image, overlay).convert("RGB")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT_PATH)

    low_confidence = sum(1 for item in items if item["low_confidence"])
    print(f"Saved: {OUTPUT_PATH}")
    print(
        f"Drew {len(items)} boxes "
        f"({low_confidence} low-confidence detections kept)."
    )


if __name__ == "__main__":
    main()
