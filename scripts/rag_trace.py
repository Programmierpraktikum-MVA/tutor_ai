#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) in sys.path:
    sys.path.remove(str(SCRIPT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import asyncio

import yaml

from config import EmbeddingsConfig, OllamaConfig, QdrantConfig
from llm.ollama import OllamaClient
from rag.prompt import build_rag_user_message, format_sources
from rag.retrieve import QdrantRetriever, RetrievalHit, expand_query


def _clean_text(text: str) -> str:
    return " ".join((text or "").split())


def _load_trace_config(path: Path) -> tuple[OllamaConfig, EmbeddingsConfig, QdrantConfig]:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    ollama_raw = raw.get("ollama") or {}
    embeddings_raw = raw.get("embeddings") or {}
    qdrant_raw = raw.get("qdrant") or {}
    if not qdrant_raw.get("url"):
        raise ValueError("Missing qdrant.url in config.")

    ollama_cfg = OllamaConfig(
        model=ollama_raw.get("model", "llama3.1"),
        host=ollama_raw.get("host"),
        system_prompt=(raw.get("prompts") or {}).get("system_prompt", OllamaConfig().system_prompt),
    )
    embeddings_cfg = EmbeddingsConfig(
        model=embeddings_raw.get("model", "nomic-embed-text:v1.5"),
        host=embeddings_raw.get("host", ollama_raw.get("host")),
        sparse_model=embeddings_raw.get("sparse_model", "Qdrant/bm25"),
    )
    qdrant_cfg = QdrantConfig(
        url=qdrant_raw["url"],
        api_key=qdrant_raw.get("api_key"),
        collection=qdrant_raw.get("collection", "tutor_ai"),
        prefer_grpc=bool(qdrant_raw.get("prefer_grpc", False)),
        dense_vector_name=qdrant_raw.get("dense_vector_name", "dense-text-vector"),
        sparse_vector_name=qdrant_raw.get("sparse_vector_name", "sparse-text-vector"),
        use_sparse=bool(qdrant_raw.get("use_sparse", True)),
        top_k=int(qdrant_raw.get("top_k", 8)),
    )
    return ollama_cfg, embeddings_cfg, qdrant_cfg


def _print_hits(hits: list[RetrievalHit], *, max_chars: int, show_full: bool) -> None:
    print(f"Retrieval hits: {len(hits)}")
    if not hits:
        return
    for index, hit in enumerate(hits, start=1):
        text = hit.text if show_full else _clean_text(hit.text)
        if not show_full and len(text) > max_chars:
            text = text[:max_chars].rstrip() + " ..."
        print(f"\n[{index}] score={hit.score:.4f}")
        print(f"source_type={hit.source_type}  course_id={hit.course_id}  chunk_index={hit.chunk_index}")
        print(f"section={hit.context_section}")
        print(f"activity={hit.context_activity}")
        print(f"file={hit.file_origin}")
        print(f"url={hit.url}")
        if hit.timestamp is not None:
            print(f"timestamp={hit.timestamp}")
        print("chunk:")
        print(text)


async def _run_once(
    question: str,
    *,
    retriever: QdrantRetriever,
    llm: OllamaClient,
    max_chars: int,
    show_full_hits: bool,
    show_system_prompt: bool,
) -> None:
    expanded_query = expand_query(question) if retriever.use_query_expansion else question
    hits = retriever.retrieve(question)
    user_prompt = build_rag_user_message(question, hits)
    answer = await llm.generate(user_prompt)

    print("\n=== Query ===")
    print(question)
    print("\n=== Expanded Query ===")
    print(expanded_query)
    print("\n=== Retrieval ===")
    _print_hits(hits, max_chars=max_chars, show_full=show_full_hits)
    if show_system_prompt:
        print("\n=== System Prompt ===")
        print(llm.system_prompt)
    print("\n=== User Prompt ===")
    print(user_prompt)
    print("\n=== LLM Output ===")
    print(answer)
    print("\n=== Sources ===")
    print(format_sources(hits))


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trace the full RAG flow: retrieval hits, final prompt, and LLM output."
    )
    parser.add_argument("--config", default=os.environ.get("CONFIG_PATH", "config.yaml"))
    parser.add_argument("--question", default=None, help="Run once instead of interactive mode.")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--score-threshold", type=float, default=None)
    parser.add_argument("--no-expand", action="store_true")
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--full-hits", action="store_true")
    parser.add_argument("--hide-system-prompt", action="store_true")
    args = parser.parse_args()

    ollama_cfg, embeddings_cfg, qdrant_cfg = _load_trace_config(Path(args.config))

    retriever = QdrantRetriever(
        qdrant_cfg=qdrant_cfg,
        embeddings_cfg=embeddings_cfg,
        top_k=args.top_k if args.top_k is not None else qdrant_cfg.top_k,
        score_threshold=args.score_threshold,
        use_query_expansion=not args.no_expand,
    )
    llm = OllamaClient(
        model=ollama_cfg.model,
        system_prompt=ollama_cfg.system_prompt,
        host=ollama_cfg.host,
    )

    if args.question:
        await _run_once(
            args.question,
            retriever=retriever,
            llm=llm,
            max_chars=max(1, args.max_chars),
            show_full_hits=args.full_hits,
            show_system_prompt=not args.hide_system_prompt,
        )
        return

    print("RAG Trace")
    print(f"Config: {args.config}")
    print("Shows retrieval hits, final prompt, and LLM output.")
    print("Type :quit to exit.\n")
    while True:
        try:
            question = input("Query> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye")
            break
        if not question:
            continue
        if question in {":quit", ":q", "quit", "exit"}:
            print("Bye")
            break
        await _run_once(
            question,
            retriever=retriever,
            llm=llm,
            max_chars=max(1, args.max_chars),
            show_full_hits=args.full_hits,
            show_system_prompt=not args.hide_system_prompt,
        )


if __name__ == "__main__":
    asyncio.run(main())
