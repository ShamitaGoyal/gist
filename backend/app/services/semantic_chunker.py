
from langchain_ollama import OllamaEmbeddings
from langchain_experimental.text_splitter import SemanticChunker


def create_semantic_splitter():
    """
    Initialize the embedding model and semantic chunker.
    """

    embeddings = OllamaEmbeddings(
        model="nomic-embed-text"
    )

    splitter = SemanticChunker(
        embeddings,
        breakpoint_threshold_type="percentile"
    )

    return splitter


def chunk_pages(pages, document_id):
    """
    Semantically split extracted PDF pages into chunks.

    Each chunk retains its source page and section information.
    """

    splitter = create_semantic_splitter()

    all_chunks = []
    chunk_index = 0

    for page in pages:

        page_number = page["page_number"]
        page_text = page["text"]

        if not page_text.strip():
            continue

        metadata = {
            "document_id": document_id,
            "page_number": page_number,
            "section_headings": page["section_headings"],
            "chunking_strategy": "semantic"
        }

        # Split this page into semantic chunks
        documents = splitter.create_documents(
            [page_text],
            metadatas=[metadata]
        )

        for document in documents:
            '''Now empty chunks won't be included, 
            and chunk indexes will remain consecutive.'''
            if not document.page_content.strip():
                continue

            document.metadata["chunk_index"] = chunk_index
            all_chunks.append(document)
            chunk_index += 1

    return all_chunks


if __name__ == "__main__":

    from app.services.pdf_service import extract_pdf

    pages = extract_pdf("data/pdf_files/meridian.pdf")

    chunks = chunk_pages(
        pages,
        document_id="meridian"
    )

    print(f"Total chunks: {len(chunks)}")

    for chunk in chunks[:3]:
        print("\n--------------------")
        print("Metadata:", chunk.metadata)
        print("Text:", chunk.page_content[:500])
    print("\n=== CHUNK STATISTICS ===")

    chunk_lengths = [
        len(chunk.page_content)
        for chunk in chunks
    ]

    print("Total chunks:", len(chunks))
    print("Average length:", sum(chunk_lengths) / len(chunk_lengths))
    print("Shortest chunk:", min(chunk_lengths))
    print("Longest chunk:", max(chunk_lengths))

    # print("\n=== EMPTY CHUNKS ===")

    # for chunk in chunks:
    #     if not chunk.page_content.strip():
    #         print("Empty chunk:", chunk.metadata)


    # print("\n=== LARGEST CHUNKS ===")

    # largest_chunks = sorted(
    #     chunks,
    #     key=lambda chunk: len(chunk.page_content),
    #     reverse=True
    # )

    # for chunk in largest_chunks[:5]:
    #     print("\nChunk index:", chunk.metadata["chunk_index"])
    #     print("Page:", chunk.metadata["page_number"])
    #     print("Characters:", len(chunk.page_content))
    #     print("Preview:", chunk.page_content[:300])
    
    # print("\n=== CHUNK BOUNDARIES ===")

    # for chunk in chunks:
    #     print(f"\nChunk {chunk.metadata['chunk_index']}")
    #     print("Page:", chunk.metadata["page_number"])
    #     print("Start:", chunk.page_content[:150].replace("\n", " "))
    #     print("End:", chunk.page_content[-150:].replace("\n", " "))