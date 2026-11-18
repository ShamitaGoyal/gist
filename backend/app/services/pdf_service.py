import re
from pathlib import Path

import pymupdf4llm


def extract_pdf(pdf_path: str):
    pages = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)

    results = []

    for page in pages:
        text = page["text"]

        # Find Markdown headings such as ## Introduction
        headings = re.findall(
            r"^#{1,6}\s+(.+)$",
            text,
            re.MULTILINE
        )

        # Remove Markdown bold markers, if present
        headings = [
            heading.replace("**", "").strip()
            for heading in headings
        ]

        results.append({
            "page_number": page["metadata"]["page_number"],
            "section_headings": headings,
            "text": text
        })

    return results


def save_markdown(pages, output_path):
    """Write every extracted page into one Markdown file."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    markdown = "\n\n".join(
        page["text"].strip()
        for page in pages
        if page["text"].strip()
    )
    output_path.write_text(markdown + "\n", encoding="utf-8")
    return output_path


if __name__ == "__main__":
    backend_root = Path(__file__).resolve().parents[2]
    pdf_path = backend_root / "data" / "pdf_files" / "meridian.pdf"
    pages = extract_pdf(str(pdf_path))

    markdown_path = save_markdown(
        pages,
        backend_root / "data" / "markdown_files" / f"{pdf_path.stem}.md",
    )

    print(f"Extracted {len(pages)} pages")
    print(f"Wrote {markdown_path}")

    for page in pages[:3]:
        print(f"\nPage {page['page_number']}")
        print("Headings:", page["section_headings"])