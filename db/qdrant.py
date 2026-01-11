from __future__ import annotations

import logging
from typing import Iterable, List, Optional

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
        distance: Distance = Distance.COSINE,
    ) -> None:
        self.collection_name = collection_name
        self.distance = distance
        self.client = QdrantClient(url=url, api_key=api_key, prefer_grpc=prefer_grpc)

    def ensure_collection(self, vector_size: int) -> None:
        if self.client.collection_exists(collection_name=self.collection_name):
            logger.info("Qdrant collection '%s' already exists.", self.collection_name)
            return

        logger.info(
            "Creating Qdrant collection '%s' with vector size %d.",
            self.collection_name,
            vector_size,
        )
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=self.distance),
        )

    def upsert(self, points: Iterable[PointStruct]) -> None:
        points_list: List[PointStruct] = list(points)
        if not points_list:
            logger.warning("No points to upsert into Qdrant.")
            return
        self.client.upsert(collection_name=self.collection_name, points=points_list)
