"""Check whether the page-4 OCR Markdown can answer one missed question.

This reads data/evaluation_results/page4_structured.md only.
It does not search Chroma, embed the question, or change the RAG pipeline.

Run from the backend directory:

    python3 tests/test_ocr_retrieval.py
"""

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_PATH = BACKEND_ROOT / "data" / "evaluation_results" / "page4_structured.md"

QUESTION = (
    "What does the dotted prefix in Meridian's data-binding specification indicate?"
)

# Words and the dotted marker "." from the question.
# "what" and "does" would match too much of the page.
KEYWORDS = ("prefix", "dotted", "data binding", '".')


def normalize(text):
    return " ".join(text.lower().replace("-", " ").split())


def parse_sections(markdown):
    """Split the file into heading blocks, keeping their body text."""

    sections = []
    heading = None
    body = []

    for line in markdown.splitlines():
        if line.startswith("##"):
            if heading is not None:
                sections.append((heading, "\n".join(body).strip()))
            heading = line.lstrip("#").strip()
            body = []
        else:
            body.append(line)

    if heading is not None:
        sections.append((heading, "\n".join(body).strip()))
    return sections


def keyword_hits(text):
    folded = normalize(text)
    return [keyword for keyword in KEYWORDS if normalize(keyword) in folded]


def numbered_explanations(body):
    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        number = stripped.split(".", 1)[0]
        if number.isdigit():
            lines.append(stripped)
    return lines


def answers_the_question(matches):
    """The question asks what the prefix indicates, not only where it appears.

    Code that contains ".name" shows the prefix in use. An explanation has
    to say that the prefix references values from the data.
    """

    for _heading, line in matches:
        folded = normalize(line)
        mentions_prefix = "prefix" in folded
        says_what_it_does = "reference" in folded and "value" in folded
        if mentions_prefix and says_what_it_does:
            return True
    return False


def main():
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    sections = parse_sections(markdown)

    print(f"Question: {QUESTION}")
    print(f"Source: {MARKDOWN_PATH}")
    print(f"Keywords: {', '.join(KEYWORDS)}")

    matched_sections = []
    evidence = []

    for heading, body in sections:
        hits = keyword_hits(body)
        if not hits:
            continue
        matched_sections.append((heading, body, hits))
        for line in body.splitlines():
            if keyword_hits(line):
                evidence.append((heading, line.strip()))

    if not matched_sections:
        print("\nNo keyword matches.")
        print("Enough to answer: no")
        return

    for heading, body, hits in matched_sections:
        print(f"\n=== {heading} ===")
        print(f"Matched keywords: {', '.join(hits)}")
        explanations = numbered_explanations(body)
        if explanations:
            print("Numbered explanations:")
            for line in explanations:
                print(f"  {line}")
        else:
            print("Matching lines:")
            for line in body.splitlines():
                if line.strip() and keyword_hits(line):
                    print(f"  {line.strip()}")

    print("\n=== EVIDENCE ===")
    for heading, line in evidence:
        print(f"- [{heading}] {line}")

    enough = answers_the_question(evidence)
    print(f"\nEnough to answer: {'yes' if enough else 'no'}")
    if enough:
        print(
            "The OCR explanation states that the prefix \".\" "
            "references values from the data."
        )
    else:
        print(
            "The matches show the prefix in use, but no line says what it indicates."
        )


if __name__ == "__main__":
    main()
