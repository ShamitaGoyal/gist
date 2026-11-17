import sys
from pathlib import Path

# Running this file directly puts tests/ on the path, not backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.llm_service import LLMService

llm = LLMService()

question = "What is semantic search?"

context = """
Semantic search finds information based on meaning
rather than relying only on exact keyword matches.
It uses embeddings to represent text as numerical vectors.
"""

answer = llm.generate_answer(
    question=question,
    context=context
)

print("\n=== LLM RESPONSE ===")
print(answer)