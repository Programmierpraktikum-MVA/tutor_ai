#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) in sys.path:
    sys.path.remove(str(SCRIPT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.ingest import ParsedChunk, build_chunks


def _load_ingest_config(path: Path) -> object | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    ollama_raw = raw.get("ollama") or {}
    return SimpleNamespace(
        ollama=SimpleNamespace(
            model=ollama_raw.get("model", "llama3.1"),
            host=ollama_raw.get("host"),
        )
    )


def _matches(chunk: ParsedChunk, args: argparse.Namespace) -> bool:
    if args.source_type and chunk.source_type != args.source_type:
        return False
    if args.file_contains and args.file_contains.casefold() not in chunk.file_origin.casefold():
        return False
    if args.text_contains and args.text_contains.casefold() not in chunk.text.casefold():
        return False
    return True


def _payload(chunk: ParsedChunk) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_type": chunk.source_type,
        "course_id": chunk.course_id,
        "file_origin": chunk.file_origin,
        "context_section": chunk.context_section,
        "context_activity": chunk.context_activity,
        "chunk_index": chunk.chunk_index,
        "url": chunk.url,
        "text": chunk.text,
    }
    if chunk.timestamp is not None:
        payload["timestamp"] = chunk.timestamp
    if chunk.page_number is not None:
        payload["page_number"] = chunk.page_number
    if chunk.page_count is not None:
        payload["page_count"] = chunk.page_count
    if chunk.text_transcript is not None:
        payload["text_transcript"] = chunk.text_transcript
    if chunk.vision_description is not None:
        payload["vision_description"] = chunk.vision_description
    return payload


def _print_summary(chunks: list[ParsedChunk]) -> None:
    print(f"Chunks: {len(chunks)}")
    if not chunks:
        return

    by_source = Counter(chunk.source_type for chunk in chunks)
    by_course = Counter(chunk.course_id for chunk in chunks)
    print("By source:")
    for source_type, count in sorted(by_source.items()):
        print(f"  {source_type}: {count}")
    print("By course:")
    for course_id, count in sorted(by_course.items()):
        print(f"  {course_id or '<none>'}: {count}")


def _print_chunk(chunk: ParsedChunk, *, index: int, max_chars: int, show_full: bool) -> None:
    print(f"\n[{index}] {chunk.source_type} course={chunk.course_id} chunk_index={chunk.chunk_index}")
    print(f"file={chunk.file_origin}")
    print(f"section={chunk.context_section}")
    print(f"activity={chunk.context_activity}")
    print(f"url={chunk.url}")
    if chunk.page_number is not None:
        print(f"page={chunk.page_number}/{chunk.page_count}")
    if chunk.timestamp is not None:
        print(f"timestamp={chunk.timestamp}")

    if chunk.vision_description is not None:
        print("vision_description:")
        print(chunk.vision_description)
    if chunk.text_transcript is not None:
        print("text_transcript:")
        transcript = chunk.text_transcript if show_full else chunk.text_transcript[:max_chars]
        print(transcript)

    print("embedding_text:")
    text = chunk.text
    if not show_full and len(text) > max_chars:
        text = text[:max_chars].rstrip() + " ..."
    print(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect the chunks produced by RAG ingestion before embedding/upsert."
    )
    parser.add_argument("--config", default=os.environ.get("CONFIG_PATH", "config.yaml"))
    parser.add_argument("--data-root", default="rag/crawler/data")
    parser.add_argument("--course-id", default=None)
    parser.add_argument("--source-type", default=None)
    parser.add_argument("--file-contains", default=None)
    parser.add_argument("--text-contains", default=None)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = _load_ingest_config(Path(args.config))
    chunks = build_chunks(Path(args.data_root), args.course_id, config=config)
    filtered = [chunk for chunk in chunks if _matches(chunk, args)]

    _print_summary(filtered)
    if args.json:
        print(json.dumps([_payload(chunk) for chunk in filtered[: args.limit]], ensure_ascii=False, indent=2))
        return

    for index, chunk in enumerate(filtered[: args.limit], start=1):
        _print_chunk(chunk, index=index, max_chars=max(1, args.max_chars), show_full=args.full)


if __name__ == "__main__":
    main()
