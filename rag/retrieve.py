# rag/retrieve.py
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from config import EmbeddingsConfig, QdrantConfig
from db.qdrant import QdrantStore
from llm.embeddings import OllamaEmbeddingClient, with_query_prefix

logger = logging.getLogger(__name__)


@dataclass
class RetrievalHit:
    score: float
    text: str
    url: str
    file_origin: str
    course_id: str
    source_type: str
    context_section: str
    context_activity: str
    chunk_index: int
    timestamp: Optional[int] = None


# --- Heuristische Query-Expansion (einfach, aber effektiv) --------------------

_KEYWORD_MAP: list[tuple[re.Pattern, list[str]]] = [
    # Prüfungen / Anmeldung
    (re.compile(r"\b(prüfung|klausur|exam|prüfungstermin|test)\b", re.I),
     ["Prüfung", "Klausur", "Exam", "Test", "Termin", "Prüfungstermin"]),
    (re.compile(r"\b(anmeldung|registrierung|einschreibung|anmelden)\b", re.I),
     ["Anmeldung", "anmelden", "Registrierung", "Einschreibung", "Frist", "Deadline"]),
    (re.compile(r"\b(prüfungsanmeldung)\b", re.I),
     ["Prüfungsanmeldung", "Anmeldung", "Klausur", "Prüfung", "Frist", "Zweittermin", "Nachtermin"]),
    (re.compile(r"\b(zweittermin|nachtermin|wiederholung)\b", re.I),
     ["Zweittermin", "Nachtermin", "Wiederholung", "zweiter Versuch"]),
    # TU Berlin / Plattformen (falls in euren Kursdaten)
    (re.compile(r"\b(isis)\b", re.I), ["ISIS", "Moodle", "Kursseite", "Link"]),
    (re.compile(r"\b(qispos|moseskonto|tu portal)\b", re.I), ["QISPOS", "Moses", "Portal", "Konto"]),
    # Organisation
    (re.compile(r"\b(frist|deadline|abgabe)\b", re.I), ["Frist", "Deadline", "Abgabe"]),
]


def expand_query(question: str) -> str:
    """
    Hängt sinnvolle Keywords an die Frage an, um Retrieval zu verbessern.
    Output ist weiterhin ein normaler Text-Query (wird dann embedded).
    """
    extras: list[str] = []
    for pattern, words in _KEYWORD_MAP:
        if pattern.search(question):
            extras.extend(words)

    # Duplikate entfernen, Reihenfolge grob behalten
    seen = set()
    uniq = []
    for w in extras:
        lw = w.lower()
        if lw in seen:
            continue
        seen.add(lw)
        uniq.append(w)

    if not uniq:
        return question

    # Frage + "Query-Booster"
    return f"{question}\n\nSuchbegriffe: " + ", ".join(uniq)


# --- Retriever ----------------------------------------------------------------

class QdrantRetriever:
    def __init__(
        self,
        qdrant_cfg: QdrantConfig,
        embeddings_cfg: EmbeddingsConfig,
        *,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        use_query_expansion: bool = True,
    ):
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.use_query_expansion = use_query_expansion

        self.store = QdrantStore(
            url=qdrant_cfg.url,
            api_key=qdrant_cfg.api_key,
            collection_name=qdrant_cfg.collection,
            prefer_grpc=qdrant_cfg.prefer_grpc,
        )
        self.embed = OllamaEmbeddingClient(model=embeddings_cfg.model, host=embeddings_cfg.host)

    def retrieve(self, query: str) -> List[RetrievalHit]:
        # 1) Query ggf. erweitern
        q = expand_query(query) if self.use_query_expansion else query

        # 2) Embedding erstellen (mit Prefix passend zu ingest)
        vector = self.embed.embed(with_query_prefix(q))

        # 3) Qdrant suchen
        try:
            points = self.store.search(
                query_vector=vector,
                limit=self.top_k,
                with_payload=True,
                score_threshold=self.score_threshold,
            )
        except Exception:
            logger.exception("Qdrant search failed")
            return []

        hits: List[RetrievalHit] = []
        for p in points:
            payload: Dict[str, Any] = getattr(p, "payload", None) or {}
            text = str(payload.get("text", "")).strip()
            if not text:
                continue

            hits.append(
                RetrievalHit(
                    score=float(getattr(p, "score", 0.0)),
                    text=text,
                    url=str(payload.get("url", "")),
                    file_origin=str(payload.get("file_origin", "")),
                    course_id=str(payload.get("course_id", "")),
                    source_type=str(payload.get("source_type", "")),
                    context_section=str(payload.get("context_section", "")),
                    context_activity=str(payload.get("context_activity", "")),
                    chunk_index=int(payload.get("chunk_index", -1) or -1),
                    timestamp=(int(payload["timestamp"]) if "timestamp" in payload else None),
                )
            )

        return hits
