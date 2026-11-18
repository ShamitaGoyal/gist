import chromadb
from langchain_core.documents import Document


class VectorStore:
    def __init__(
        self,
        persist_directory="data/chroma_db",
        collection_name="gist_documents",
        client=None,
    ):
        # The defaults stay the saved gist_documents collection.
        # Tests pass an in-memory client so they do not write that collection.
        if client is None:
            self.client = chromadb.PersistentClient(
                path=persist_directory
            )
        else:
            self.client = client

        self.collection = self.client.get_or_create_collection(
            name=collection_name
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
            headings = metadata.get("section_headings", [])
            # Stored metadata cannot hold a list. Leave strings alone so a
            # restored record is not joined a second time.
            if isinstance(headings, list):
                metadata["section_headings"] = " | ".join(
                    str(part) for part in headings
                )

            metadatas.append(metadata)

        self.collection.upsert(
            ids=ids,
            documents=[chunk.page_content for chunk in chunks],
            embeddings=embeddings,
            metadatas=metadatas
        )

        return len(ids)

    def records_for_document(self, document_id):
        """Return the stored rows for one document, or empty lists."""

        stored = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas", "embeddings"],
        )
        return {
            "ids": _stored_list(stored.get("ids")),
            "documents": _stored_list(stored.get("documents")),
            "metadatas": _stored_list(stored.get("metadatas")),
            "embeddings": _stored_list(stored.get("embeddings")),
        }

    def documents_for(self, document_id):
        """Load one document's chunks in chunk_index order."""

        stored = self.records_for_document(document_id)
        documents = [
            Document(page_content=text, metadata=dict(metadata))
            for text, metadata in zip(stored["documents"], stored["metadatas"])
        ]
        documents.sort(key=lambda document: int(document.metadata["chunk_index"]))
        return documents

    def delete_ids(self, ids):
        if ids:
            self.collection.delete(ids=list(ids))

    def delete_document(self, document_id):
        """Remove one document's chunk ids. Other documents stay in the collection."""

        stored = self.collection.get(where={"document_id": document_id})
        ids = _stored_list(stored.get("ids"))
        self.delete_ids(ids)
        return len(ids)

    def replace_document(self, chunks, embeddings):
        """Replace one document after the new chunks and embeddings exist.

        The previous rows are snapshotted first. They are deleted only after
        the new ids are stored. A failure restores that snapshot and removes
        any new ids the failed attempt added. Other documents are not queried.
        """

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Embedding count {len(embeddings)} does not match "
                f"chunk count {len(chunks)}"
            )
        document_ids = {chunk.metadata.get("document_id") for chunk in chunks}
        if document_ids != {chunks[0].metadata.get("document_id")}:
            raise ValueError("A replacement must contain one document_id")
        document_id = chunks[0].metadata["document_id"]
        snapshot = self.records_for_document(document_id)
        new_ids = [
            f"{document_id}_{int(chunk.metadata['chunk_index'])}"
            for chunk in chunks
        ]
        try:
            stored_count = self.add_documents(chunks, embeddings)
            found = self.collection.get(ids=new_ids)
            if set(found["ids"]) != set(new_ids) or len(found["ids"]) != len(new_ids):
                raise RuntimeError(
                    f"Stored chunk ids for {document_id} do not match the replacement"
                )
            stale_ids = [
                chunk_id
                for chunk_id in snapshot["ids"]
                if chunk_id not in set(new_ids)
            ]
            self.delete_ids(stale_ids)
            return stored_count
        except Exception:
            self._restore_snapshot(snapshot, new_ids)
            raise

    def _restore_snapshot(self, snapshot, new_ids):
        """Put a document's previous rows back and drop ids from a failed write."""

        previous_ids = list(snapshot["ids"])
        if previous_ids:
            self.collection.upsert(
                ids=previous_ids,
                documents=list(snapshot["documents"]),
                metadatas=list(snapshot["metadatas"]),
                embeddings=[
                    [float(value) for value in vector]
                    for vector in snapshot["embeddings"]
                ],
            )
        extra_ids = [
            chunk_id for chunk_id in new_ids if chunk_id not in set(previous_ids)
        ]
        if extra_ids:
            self.collection.delete(ids=extra_ids)

    def search(self, query_embedding, top_k=3, max_distance=0.75):

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        # Find the chunks that pass our distance threshold
        valid_indices = [
            i
            for i, distance in enumerate(results["distances"][0])
            if distance <= max_distance
        ]

        # Keep only the relevant chunks
        filtered_results = {
            "ids": [[results["ids"][0][i] for i in valid_indices]],
            "documents": [[results["documents"][0][i] for i in valid_indices]],
            "metadatas": [[results["metadatas"][0][i] for i in valid_indices]],
            "distances": [[results["distances"][0][i] for i in valid_indices]]
        }

        return filtered_results


def _stored_list(value):
    """Chroma may return None or a numpy array. Neither should use truthiness."""

    if value is None:
        return []
    return list(value)