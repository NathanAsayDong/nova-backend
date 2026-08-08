import os

from openai import OpenAI


class EmbeddingService:
    """
    Text -> vector embeddings for memory chunk storage and RAG lookup.

    Uses OpenAI text-embedding-3-small (1536 dims), matching the
    memory_chunk.embedding Vector(1536) column.
    """

    MODEL = "text-embedding-3-small"

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.MODEL, input=texts)
        # The API preserves input order; sort defensively by index anyway.
        return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]
