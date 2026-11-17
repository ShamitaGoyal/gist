
from langchain_community.retrievers import BM25Retriever
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_ollama import OllamaEmbeddings


class HybridSearchService:
    def __init__(self, chunks):
        # 1. Create the BM25 keyword retriever
        self.bm25_retriever = BM25Retriever.from_documents(
            chunks,
            k=3
        )

        # 2. Connect to the existing ChromaDB collection
        embeddings = OllamaEmbeddings(
            model="nomic-embed-text"
        )

        self.vector_store = Chroma(
            collection_name="gist_documents",
            persist_directory="data/chroma_db",
            embedding_function=embeddings
        )

        # 3. Create the semantic retriever
        self.semantic_retriever = self.vector_store.as_retriever(
            search_kwargs={"k": 3}
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
        return self.hybrid_retriever.invoke(query)
