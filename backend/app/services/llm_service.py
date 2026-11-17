
from langchain_ollama import ChatOllama


class LLMService:
    def __init__(self):
        self.model = ChatOllama(
            model="llama3.2:1b",
            temperature=0
        )

    def generate_answer(self, question, context):
        prompt = f"""
        You are Gist, an AI research assistant.

        Answer the user's question using only the provided context.

        If the context does not contain enough information,
        say that the document does not provide enough information.

        Do not invent facts.

        DOCUMENT CONTEXT:
        {context}

        USER QUESTION:
        {question}

        ANSWER:
        """

        response = self.model.invoke(prompt)

        return response.content
