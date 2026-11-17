from langchain_community.retrievers import BM25Retriever


class BM25Service:

    def __init__(self, chunks):
        self.retriever = BM25Retriever.from_documents(
            chunks,
            k=3
        )

    def search(self, query):
        return self.retriever.invoke(query)