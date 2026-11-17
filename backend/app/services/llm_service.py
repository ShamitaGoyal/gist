
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

        Answer the user's question using only the provided document context.

        Rules:
        1. Answer directly and clearly.
        2. Use only information supported by the context.
        3. Include page citations like [Page 3].
        4. Do not invent facts.
        5. If the context does not contain enough information,
        clearly explain what information is missing.
        6. Do not say the document lacks information if you
        have already answered the question using the context.
        7. Do not repeat your answer or add unnecessary conclusions.

        DOCUMENT CONTEXT:
        {context}

        USER QUESTION:
        {question}

        ANSWER:
        """

        response = self.model.invoke(prompt)
        return response.content
