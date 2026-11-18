from langchain_community.retrievers import BM25Retriever
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_ollama import OllamaEmbeddings


class HybridSearchService:
    def __init__(
        self,
        chunks,
        document_id=None,
        chroma_client=None,
        collection_name="gist_documents",
        persist_directory="data/chroma_db",
        source_type=None,
    ):
        # BM25 has no metadata filter, so restricted searches are built
        # only from chunks that already match the document and source type.
        if document_id is not None:
            chunks = [
                chunk
                for chunk in chunks
                if chunk.metadata.get("document_id") == document_id
            ]
        if source_type is not None:
            chunks = [
                chunk
                for chunk in chunks
                if chunk.metadata.get("source_type") == source_type
            ]
        self.document_id = document_id
        self.source_type = source_type

        # 1. Create the BM25 keyword retriever
        self.bm25_retriever = BM25Retriever.from_documents(
            chunks,
            k=3
        )

        # 2. Connect to the Chroma collection that holds the embeddings
        embeddings = OllamaEmbeddings(
            model="nomic-embed-text"
        )
        if chroma_client is None:
            self.vector_store = Chroma(
                collection_name=collection_name,
                persist_directory=persist_directory,
                embedding_function=embeddings
            )
        else:
            self.vector_store = Chroma(
                client=chroma_client,
                collection_name=collection_name,
                embedding_function=embeddings
            )

        # 3. Create the semantic retriever
        search_kwargs = {"k": 3}
        metadata_filter = _metadata_filter(document_id, source_type)
        if metadata_filter is not None:
            search_kwargs["filter"] = metadata_filter
        self.semantic_retriever = self.vector_store.as_retriever(
            search_kwargs=search_kwargs
        )

        # 4. Combine both retrievers using RRF
        self.hybrid_retriever = EnsembleRetriever(
            retrievers=[
                self.bm25_retriever,
                self.semantic_retriever
            ],
            weights=[0.5, 0.5]
        )

    def search(self, query):
        results = self.hybrid_retriever.invoke(query)
        if self.document_id is None and self.source_type is None:
            return results
        return [
            document
            for document in results
            if _matches(document, self.document_id, self.source_type)
        ]


def _metadata_filter(document_id, source_type):
    clauses = []
    if document_id is not None:
        clauses.append({"document_id": document_id})
    if source_type is not None:
        clauses.append({"source_type": source_type})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _matches(document, document_id, source_type):
    metadata = document.metadata
    if document_id is not None and metadata.get("document_id") != document_id:
        return False
    if source_type is not None and metadata.get("source_type") != source_type:
        return False
    return True
