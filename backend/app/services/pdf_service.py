import re
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


if __name__ == "__main__":
    pages = extract_pdf("data/pdf_files/meridian.pdf")

    print(f"Extracted {len(pages)} pages")

    for page in pages[:3]:
        print(f"\nPage {page['page_number']}")
        print("Headings:", page["section_headings"])