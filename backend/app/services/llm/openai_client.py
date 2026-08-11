"""The only backend module that communicates with OpenAI."""

from openai import OpenAI

from app.core.config import settings


class OpenAIConfigurationError(RuntimeError):
    pass


class OpenAIService:
    def __init__(self) -> None:
        if not settings.openai_api_key or not settings.openai_chat_model:
            raise OpenAIConfigurationError(
                "OpenAI is not configured. Add OPENAI_API_KEY and OPENAI_CHAT_MODEL to backend/.env, then restart the backend."
            )
        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate_answer(self, question: str, context: str) -> str:
        response = self.client.responses.create(
            model=settings.openai_chat_model,
            instructions=("You are an enterprise knowledge assistant. Answer only from the supplied "
                          "document context. Cite evidence as [Source N]. If evidence is insufficient, say so."),
            input=f"Question:\n{question}\n\nDocument context:\n{context}",
        )
        return response.output_text.strip()

    def compare_documents(self, name_a: str, text_a: str, name_b: str, text_b: str) -> str:
        response = self.client.responses.create(
            model=settings.openai_chat_model,
            instructions=("Compare only the two supplied documents. Use headings: Overview, Major Changes, "
                          "Added or Removed Content, Changed Rules, Potential Impact. Do not invent differences."),
            input=f"DOCUMENT A: {name_a}\n{text_a[:24000]}\n\nDOCUMENT B: {name_b}\n{text_b[:24000]}",
        )
        return response.output_text.strip()
