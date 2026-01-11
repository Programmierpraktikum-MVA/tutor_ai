from __future__ import annotations

import logging
from typing import Iterable, List, Optional

import ollama  # type: ignore[import]


logger = logging.getLogger(__name__)


DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


class OllamaEmbeddingClient:
    """Small wrapper for Ollama embeddings."""

    def __init__(self, model: str, host: Optional[str] = None):
        self.model_name = model
        self.client = ollama.Client(host=host) if host else ollama.Client()

    def embed(self, text: str) -> List[float]:
        logger.debug("Embedding text (%d chars) with model %s", len(text), self.model_name)
        response = self.client.embeddings(model=self.model_name, prompt=text)
        embedding = response.get("embedding")
        if not embedding:
            raise ValueError("Ollama returned an empty embedding.")
        return embedding

    def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for text in texts:
            embeddings.append(self.embed(text))
        return embeddings


def with_document_prefix(text: str) -> str:
    return f"{DOCUMENT_PREFIX}{text}"


def with_query_prefix(text: str) -> str:
    return f"{QUERY_PREFIX}{text}"
