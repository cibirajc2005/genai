"""OpenAI embeddings with a deterministic offline fallback for local usability."""

import hashlib
import math
import re

from openai import OpenAI

from app.core.config import settings

LOCAL_DIMENSIONS = 384


def local_embedding(text: str) -> list[float]:
    """Create a stable hashed bag-of-words vector when OpenAI is unavailable."""
    vector = [0.0] * LOCAL_DIMENSIONS
    for word in re.findall(r"[a-z0-9]{2,}", text.lower()):
        digest = hashlib.sha256(word.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % LOCAL_DIMENSIONS
        vector[index] += -1.0 if digest[4] & 1 else 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class EmbeddingService:
    def embed(self, texts: list[str]) -> tuple[list[list[float]], str]:
        if settings.openai_api_key and settings.openai_embedding_model:
            try:
                response = OpenAI(api_key=settings.openai_api_key).embeddings.create(
                    model=settings.openai_embedding_model, input=texts
                )
                return [item.embedding for item in response.data], settings.openai_embedding_model
            except Exception:
                # Indexing remains usable offline or when the account is rate-limited.
                pass
        return [local_embedding(text) for text in texts], "local-hash-384"


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
