
from langchain_ollama import OllamaEmbeddings


class EmbeddingService:

    def __init__(self):
        self.model = OllamaEmbeddings(
            model="nomic-embed-text"
        )

    def embed_documents(self, texts):
        # A list of text chunks -> A list of vectors
        return self.model.embed_documents(texts)

    def embed_query(self, query):
        # One question ->	One vector
        return self.model.embed_query(query)
