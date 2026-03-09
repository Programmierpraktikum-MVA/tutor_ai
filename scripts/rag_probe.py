#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Avoid shadowing stdlib `token` via `scripts/token.py` when importing other modules.
if str(SCRIPT_DIR) in sys.path:
    sys.path.remove(str(SCRIPT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import EmbeddingsConfig, QdrantConfig
from rag.retrieve import QdrantRetriever, RetrievalHit, expand_query


def _clean_text(text: str) -> str:
    return " ".join((text or "").split())


def _print_hits(hits: Iterable[RetrievalHit], max_chars: int, show_full: bool) -> None:
    hits = list(hits)
    print(f"Treffer: {len(hits)}")
    if not hits:
        return

    for i, hit in enumerate(hits, start=1):
        chunk = _clean_text(hit.text)
        if not show_full and len(chunk) > max_chars:
            chunk = chunk[:max_chars].rstrip() + " ..."

        print(f"\n[{i}] score={hit.score:.4f}")
        print(f"source_type={hit.source_type}  course_id={hit.course_id}  chunk_index={hit.chunk_index}")
        print(f"section={hit.context_section}")
        print(f"activity={hit.context_activity}")
        print(f"file={hit.file_origin}")
        print(f"url={hit.url}")
        if hit.timestamp is not None:
            print(f"timestamp={hit.timestamp}")
        page_number = getattr(hit, "page_number", None)
        page_count = getattr(hit, "page_count", None)
        if page_number is not None:
            print(f"page={page_number}/{page_count}")
        print("chunk:")
        print(chunk)


def _print_json(hits: Iterable[RetrievalHit]) -> None:
    payload = []
    for h in hits:
        payload.append(
            {
                "score": h.score,
                "text": h.text,
                "url": h.url,
                "file_origin": h.file_origin,
                "course_id": h.course_id,
                "source_type": h.source_type,
                "context_section": h.context_section,
                "context_activity": h.context_activity,
                "chunk_index": h.chunk_index,
                "timestamp": h.timestamp,
                "page_number": h.page_number,
                "page_count": h.page_count,
                "text_transcript": h.text_transcript,
                "vision_description": h.vision_description,
            }
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _load_probe_config(path: str) -> tuple[QdrantConfig, EmbeddingsConfig]:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    qdrant_raw = raw.get("qdrant") or {}
    embeddings_raw = raw.get("embeddings") or {}
    ollama_raw = raw.get("ollama") or {}

    url = qdrant_raw.get("url")
    if not url:
        raise ValueError("Missing qdrant.url in config.")

    qdrant_cfg = QdrantConfig(
        url=url,
        api_key=qdrant_raw.get("api_key"),
        collection=qdrant_raw.get("collection", "tutor_ai"),
        prefer_grpc=bool(qdrant_raw.get("prefer_grpc", False)),
        dense_vector_name=qdrant_raw.get("dense_vector_name", "dense-text-vector"),
        sparse_vector_name=qdrant_raw.get("sparse_vector_name", "sparse-text-vector"),
        use_sparse=bool(qdrant_raw.get("use_sparse", True)),
        top_k=int(qdrant_raw.get("top_k", 8)),
    )

    embeddings_cfg = EmbeddingsConfig(
        model=embeddings_raw.get("model", "nomic-embed-text:v1.5"),
        host=embeddings_raw.get("host", ollama_raw.get("host")),
        sparse_model=embeddings_raw.get("sparse_model", "Qdrant/bm25"),
    )
    return qdrant_cfg, embeddings_cfg


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive RAG probe: query Qdrant retrieval directly without LLM."
    )
    parser.add_argument("--config", default=os.environ.get("CONFIG_PATH", "config.yaml"))
    parser.add_argument("--top-k", type=int, default=None, help="Override top_k from config")
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=None,
        help="Optional score threshold passed to Qdrant",
    )
    parser.add_argument(
        "--no-expand",
        action="store_true",
        help="Disable query expansion in retriever",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw hits as JSON instead of formatted output",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Max chars shown per chunk in formatted mode",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Show full chunk text (no truncation)",
    )
    parser.add_argument(
        "--show-expanded",
        action="store_true",
        help="Print the expanded retrieval query before the hits",
    )
    args = parser.parse_args()

    qdrant_cfg, embeddings_cfg = _load_probe_config(args.config)

    top_k = args.top_k if args.top_k is not None else qdrant_cfg.top_k
    retriever = QdrantRetriever(
        qdrant_cfg=qdrant_cfg,
        embeddings_cfg=embeddings_cfg,
        top_k=top_k,
        score_threshold=args.score_threshold,
        use_query_expansion=not args.no_expand,
    )

    print("RAG Probe (ohne LLM)")
    print(f"Config: {args.config}")
    print(f"Collection: {qdrant_cfg.collection}")
    print(f"top_k: {top_k}")
    print("Tippe eine Frage. Mit :quit beenden.\n")

    while True:
        try:
            query = input("Query> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye")
            break

        if not query:
            continue
        if query in {":quit", ":q", "quit", "exit"}:
            print("Bye")
            break

        expanded_query = expand_query(query) if retriever.use_query_expansion else query
        if args.show_expanded:
            print("\nExpanded query:")
            print(expanded_query)
        hits = retriever.retrieve(query)
        if args.json:
            _print_json(hits)
        else:
            _print_hits(hits, max_chars=max(1, args.max_chars), show_full=args.full)


if __name__ == "__main__":
    main()
