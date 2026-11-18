"""Grounded answers use retrieved text, and citations come from chunk metadata.

Run from the backend directory:

    python3 tests/test_grounding.py
"""

import sys
from pathlib import Path

from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grounding import INSUFFICIENT_MESSAGE, build_grounded_prompt
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService


class RecordingLLM:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def generate_answer(self, question, context):
        self.calls.append((question, context))
        return self.answer


def chunk(document_id, index, page, text, source_type="pdf_extraction"):
    return Document(
        page_content=text,
        metadata={
            "document_id": document_id,
            "chunk_index": index,
            "page_number": page,
            "source_type": source_type,
            "section_headings": [],
        },
    )


def test_prompt_and_context():
    prompt = build_grounded_prompt(
        "How many roles?",
        "Meridian provides twelve default roles.",
    )
    assert "USER QUESTION:" in prompt
    assert "RETRIEVED DOCUMENT CONTEXT:" in prompt
    assert "INSTRUCTIONS:" in prompt
    assert "EXPECTED ANSWER FORMAT:" in prompt
    assert "untrusted reference material" in prompt
    assert "outside knowledge" in prompt
    assert "How many roles?" in prompt
    assert "twelve default roles" in prompt

    recorder = RecordingLLM("Meridian provides twelve default roles.")
    service = RAGService(llm_service=recorder)
    result = service._compose(
        "How many roles?",
        [chunk("meridian", 4, 5, "Meridian provides twelve default roles.")],
        figure_retrieval_used=False,
    )
    assert recorder.calls
    assert "twelve default roles" in recorder.calls[0][1]
    assert result["grounding_status"] == "grounded"
    assert result["sources"][0]["chunk_id"] == "meridian_4"
    assert "[Source: meridian_4, Page 5]" in result["answer"]
    print("Prompt receives the retrieved context and a real citation.")


def test_insufficient_context_skips_the_model():
    recorder = RecordingLLM("This should not be used.")
    service = RAGService(llm_service=recorder)
    result = service._compose("What is the phone number?", [], False)
    assert recorder.calls == []
    assert result["grounding_status"] == "insufficient_context"
    assert result["sources"] == []
    assert INSUFFICIENT_MESSAGE in result["answer"]
    print("Missing context does not call the model.")


def test_invented_citations_are_removed():
    recorder = RecordingLLM(
        "Meridian provides twelve default roles. [Source: fake_999, Page 99]"
    )
    service = RAGService(llm_service=recorder)
    result = service._compose(
        "How many roles?",
        [chunk("meridian", 4, 5, "Meridian provides twelve default roles.")],
        False,
    )
    assert "fake_999" not in result["answer"]
    assert "Page 99" not in result["answer"]
    assert "[Source: meridian_4, Page 5]" in result["answer"]
    print("Invented source ids are removed.")


def test_partial_overlap_is_not_marked_grounded():
    recorder = RecordingLLM(
        "Meridian provides twelve default roles. "
        "Semantic zooming uses a secret neural renderer."
    )
    service = RAGService(llm_service=recorder)
    result = service._compose(
        "How many roles?",
        [chunk("meridian", 4, 5, "Meridian provides twelve default roles.")],
        False,
    )
    assert result["grounding_status"] == "partially_grounded"
    print("Unsupported sentences stay partially grounded.")


def test_providers_share_the_prompt_builder():
    class Capture:
        def __init__(self):
            self.prompt = ""

        def generate(self, prompt):
            self.prompt = prompt
            return "Meridian provides roles."

    capture = Capture()
    service = LLMService(provider_impl=capture)
    service.generate_answer("How many roles?", "Meridian provides roles.")
    expected = build_grounded_prompt("How many roles?", "Meridian provides roles.")
    assert capture.prompt == expected
    print("The service sends the shared grounded prompt.")


def main():
    test_prompt_and_context()
    test_insufficient_context_skips_the_model()
    test_invented_citations_are_removed()
    test_partial_overlap_is_not_marked_grounded()
    test_providers_share_the_prompt_builder()
    print("Passed.")


if __name__ == "__main__":
    main()
