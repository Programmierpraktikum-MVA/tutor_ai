# db/qdrant.py
from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

from qdrant_client import QdrantClient
from dataclasses import dataclass
from qdrant_client.http.models import Distance, PointStruct, VectorParams

try:  # qdrant-client >= 1.7
    from qdrant_client.http.models import SparseVectorParams
except Exception:  # pragma: no cover - optional dependency
    SparseVectorParams = None

logger = logging.getLogger(__name__)
DEFAULT_UPSERT_BATCH_SIZE = 128


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

    def ensure_collection(
        self,
        vector_size: int,
        *,
        dense_vector_name: str = "dense-text-vector",
        sparse_vector_name: str = "sparse-text-vector",
        use_sparse: bool = False,
    ) -> None:
        # create collection if needed
        exists = self.client.collection_exists(collection_name=self.collection_name)
        if exists:
            return

        logger.info(
            "Creating Qdrant collection '%s' with vector size %d",
            self.collection_name,
            vector_size,
        )
        vectors_config = {
            dense_vector_name: VectorParams(size=vector_size, distance=Distance.COSINE),
        }
        if use_sparse:
            if SparseVectorParams is None:
                raise RuntimeError("Sparse vectors requested but SparseVectorParams is unavailable.")
            sparse_vectors_config = {sparse_vector_name: SparseVectorParams()}
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )
        else:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=vectors_config,
            )

    def upsert(self, points: List[PointStruct]) -> None:
        if not points:
            return
        batch_size = _resolve_upsert_batch_size()
        total = len(points)
        for start in range(0, total, batch_size):
            batch = points[start : start + batch_size]
            logger.info(
                "Upserting Qdrant batch %d-%d/%d into '%s'",
                start + 1,
                start + len(batch),
                total,
                self.collection_name,
            )
            self.client.upsert(collection_name=self.collection_name, points=batch)

    def search(
        self,
        *,
        query_vector: List[float],
        limit: int = 5,
        with_payload: bool = True,
        score_threshold: Optional[float] = None,
        vector_name: Optional[str] = None,
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
            params = dict(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                with_payload=with_payload,
                score_threshold=score_threshold,
            )
            if vector_name:
                params["using"] = vector_name
            params.update(kwargs)
            res = self.client.query_points(**params)
            return getattr(res, "points", res)

        # MID: search_points
        if hasattr(self.client, "search_points"):
            params = dict(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=with_payload,
                score_threshold=score_threshold,
            )
            if vector_name:
                params["vector_name"] = vector_name
            params.update(kwargs)
            return self.client.search_points(**params)

        # OLD: search
        params = dict(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=with_payload,
            score_threshold=score_threshold,
        )
        if vector_name:
            params["vector_name"] = vector_name
        params.update(kwargs)
        return self.client.search(**params)

    def hybrid_search(
        self,
        *,
        dense_vector: List[float],
        sparse_vector: Any,
        limit: int = 5,
        with_payload: bool = True,
        score_threshold: Optional[float] = None,
        dense_vector_name: str = "dense-text-vector",
        sparse_vector_name: str = "sparse-text-vector",
    ):
        extended_limit = _safe_extend_limit(limit)
        dense_hits = self.search(
            query_vector=dense_vector,
            limit=extended_limit,
            with_payload=with_payload,
            score_threshold=score_threshold,
            vector_name=dense_vector_name,
        )
        sparse_hits = self.search(
            query_vector=sparse_vector,
            limit=extended_limit,
            with_payload=with_payload,
            score_threshold=score_threshold,
            vector_name=sparse_vector_name,
        )
        return _rrf_merge(dense_hits, sparse_hits, limit=limit)


@dataclass
class HybridHit:
    id: Any
    payload: Any
    score: float


def _rrf_merge(*lists: List[Any], limit: int = 5, k: int = 60) -> List[HybridHit]:
    scores: dict[Any, float] = {}
    payloads: dict[Any, Any] = {}
    for hits in lists:
        for rank, hit in enumerate(hits, start=1):
            hid = getattr(hit, "id", None)
            if hid is None:
                continue
            scores[hid] = scores.get(hid, 0.0) + 1.0 / (k + rank)
            if hid not in payloads:
                payloads[hid] = getattr(hit, "payload", None)
    merged = [
        HybridHit(id=hid, payload=payloads.get(hid), score=score)
        for hid, score in scores.items()
    ]
    merged.sort(key=lambda item: item.score, reverse=True)
    return merged[:limit]


def _safe_extend_limit(limit: int) -> int:
    return max(limit * 2, limit + 10)


def _resolve_upsert_batch_size() -> int:
    raw = os.environ.get("QDRANT_UPSERT_BATCH_SIZE")
    if not raw:
        return DEFAULT_UPSERT_BATCH_SIZE
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "Invalid QDRANT_UPSERT_BATCH_SIZE=%r; falling back to %d.",
            raw,
            DEFAULT_UPSERT_BATCH_SIZE,
        )
        return DEFAULT_UPSERT_BATCH_SIZE
    return max(1, value)
