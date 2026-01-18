# db/qdrant.py
from __future__ import annotations

import logging
from typing import Any, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

logger = logging.getLogger(__name__)


class QdrantStore:
    def __init__(
        self,
        url: str,
        api_key: Optional[str],
        collection_name: str,
        prefer_grpc: bool = False,
    ):
        self.collection_name = collection_name
        self.client = QdrantClient(url=url, api_key=api_key, prefer_grpc=prefer_grpc)

    def ensure_collection(self, vector_size: int) -> None:
        # create collection if needed
        exists = self.client.collection_exists(collection_name=self.collection_name)
        if exists:
            return

        logger.info(
            "Creating Qdrant collection '%s' with vector size %d",
            self.collection_name,
            vector_size,
        )
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert(self, points: List[PointStruct]) -> None:
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(
        self,
        *,
        query_vector: List[float],
        limit: int = 5,
        with_payload: bool = True,
        score_threshold: Optional[float] = None,
        **kwargs: Any,
    ):
        """
        Compatibility wrapper:

        - newer qdrant-client: client.query_points(...).points
        - some versions:       client.search_points(...)
        - older versions:      client.search(...)
        """
        # NEW: query_points (recommended)
        if hasattr(self.client, "query_points"):
            res = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                with_payload=with_payload,
                score_threshold=score_threshold,
                **kwargs,
            )
            return getattr(res, "points", res)

        # MID: search_points
        if hasattr(self.client, "search_points"):
            return self.client.search_points(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=with_payload,
                score_threshold=score_threshold,
                **kwargs,
            )

        # OLD: search
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=with_payload,
            score_threshold=score_threshold,
            **kwargs,
        )
