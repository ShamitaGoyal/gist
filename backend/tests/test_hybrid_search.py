
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pdf_service import extract_pdf
from app.services.semantic_chunker import chunk_pages
from app.services.hybrid_search import HybridSearchService


# 1. Extract the PDF
pages = extract_pdf("data/pdf_files/meridian.pdf")

# 2. Create semantic chunks
chunks = chunk_pages(pages, document_id="meridian")

# 3. Initialize hybrid search
hybrid_search = HybridSearchService(chunks)

# 4. Search
query = "What does the Meridian specification define about views and data binding?"
results = hybrid_search.search(query)

# 5. Display results
print("=== HYBRID SEARCH RESULTS ===")
print("Query:", query)
print("Chunks retrieved:", len(results))

for i, chunk in enumerate(results, start=1):
    print(f"\n--- Result {i} ---")
    print("Page:", chunk.metadata["page_number"])
    print("Chunk ID:", chunk.metadata["chunk_index"])
    print("Text:")
    print(chunk.page_content[:500])
