import os
import threading
from collections import OrderedDict

from openai import OpenAI

# Single-query embeddings are cached because retrieval now runs on every turn,
# and a conversation asks the same thing more than once: "what did we decide",
# a repeated question, a retry after a failed tool call. A hit turns a ~100ms
# network round trip into a dict lookup on the critical path of a spoken reply.
# Bounded because it is keyed by arbitrary user text.
_QUERY_CACHE_SIZE = 256


class EmbeddingService:
    """
    Text -> vector embeddings for memory chunk storage and RAG lookup.

    Uses OpenAI text-embedding-3-small (1536 dims), matching the
    memory_chunk.embedding Vector(1536) column.
    """

    MODEL = "text-embedding-3-small"

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._query_cache: OrderedDict[str, list[float]] = OrderedDict()
        # Retrieval runs on a worker thread while the turn's other setup work
        # runs on the caller's, so the cache is reachable from both.
        self._cache_lock = threading.Lock()

    def embed_text(self, text: str) -> list[float]:
        """Embed one string, memoized on the exact text."""
        with self._cache_lock:
            cached = self._query_cache.get(text)
            if cached is not None:
                self._query_cache.move_to_end(text)
                return cached

        embedding = self.embed_texts([text])[0]

        with self._cache_lock:
            self._query_cache[text] = embedding
            self._query_cache.move_to_end(text)
            while len(self._query_cache) > _QUERY_CACHE_SIZE:
                self._query_cache.popitem(last=False)
        return embedding

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.MODEL, input=texts)
        # The API preserves input order; sort defensively by index anyway.
        return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]
