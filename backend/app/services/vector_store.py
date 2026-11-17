import chromadb


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path="data/chroma_db"
        )

        self.collection = self.client.get_or_create_collection(
            name="gist_documents"
        )

    def add_documents(self, chunks, embeddings):
        ids = []
        metadatas = []

        for chunk in chunks:
            chunk_id = (
                f"{chunk.metadata['document_id']}_"
                f"{chunk.metadata['chunk_index']}"
            )
            ids.append(chunk_id)

            metadata = chunk.metadata.copy()

            # Convert section headings from a list into a string
            metadata["section_headings"] = " | ".join(
                metadata["section_headings"]
            )

            metadatas.append(metadata)

        self.collection.upsert(
            ids=ids,
            documents=[chunk.page_content for chunk in chunks],
            embeddings=embeddings,
            metadatas=metadatas
        )

        return len(ids)
    
    def search(self, query_embedding, top_k=3):
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        return results