from __future__ import annotations

import argparse
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import NAMESPACE_URL, uuid5

from qdrant_client.http.models import PointStruct

from config import Config
from db.qdrant import QdrantStore
from llm.embeddings import OllamaEmbeddingClient, with_document_prefix
from log_config import setup_logging
from rag.chunkers import chunk_text

logger = logging.getLogger(__name__)

SECTION_PREFIX = "Abschnitt "
SECTION_SUFFIX = " ausw\u00e4hlen"
ACTIVITY_PREFIX = "Aktivit\u00e4t "
ACTIVITY_SUFFIX = " ausw\u00e4hlen"

NOISE_LINES = {
    "Einklappen",
    "Ausklappen",
    "Alles einklappen",
    "Alles aufklappen",
    "Verzeichnis",
    "Externes Tool",
    "Datei",
    "Textseite",
}

URL_PATTERN = re.compile(r"https?://\S+")


@dataclass
class ParsedChunk:
    text: str
    source_type: str
    context_section: str
    context_activity: str
    url: str
    file_origin: str
    course_id: str
    chunk_index: int
    timestamp: Optional[int] = None


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_label(line: str, prefix: str, suffix: str) -> Optional[str]:
    if not line.startswith(prefix) or not line.endswith(suffix):
        return None
    inner = line[len(prefix) : len(line) - len(suffix)]
    return inner.strip() if inner else None


def _clean_join(parts: List[str]) -> str:
    merged = " ".join(part.strip() for part in parts if part.strip())
    merged = re.sub(r"\s+([,.;:])", r"\1", merged)
    merged = re.sub(r"\s+", " ", merged)
    return merged.strip()


def _extract_first_url(lines: List[str]) -> Optional[str]:
    for line in lines:
        match = URL_PATTERN.search(line)
        if match:
            return match.group(0).rstrip(").,;")
    return None


def _course_url(course_id: str) -> str:
    return f"https://isis.tu-berlin.de/course/view.php?id={course_id}"


def parse_course_info_file(path: Path, course_id: str) -> List[ParsedChunk]:
    raw = _load_json(path)
    if not isinstance(raw, list):
        logger.warning("Skipping %s: expected list payload.", path)
        return []

    file_origin = path.name
    current_section = "Course Overview"
    current_activity: Optional[str] = None
    buffer: List[str] = []
    urls: List[str] = []
    chunks: List[ParsedChunk] = []
    chunk_counter = 0

    def flush() -> None:
        nonlocal chunk_counter
        if not buffer:
            return
        text = _clean_join(buffer)
        if not text:
            buffer.clear()
            urls.clear()
            return
        activity = current_activity or "Section Overview"
        section = current_section or "Unlabeled Section"
        url = _extract_first_url(urls) or _course_url(course_id)
        for part in chunk_text(text):
            chunks.append(
                ParsedChunk(
                    text=part,
                    source_type="course_info",
                    context_section=section,
                    context_activity=activity,
                    url=url,
                    file_origin=file_origin,
                    course_id=course_id,
                    chunk_index=chunk_counter,
                )
            )
            chunk_counter += 1
        buffer.clear()
        urls.clear()

    for entry in raw:
        if not isinstance(entry, str):
            continue
        line = entry.strip()
        if not line or line in NOISE_LINES:
            continue

        section_label = _extract_label(line, SECTION_PREFIX, SECTION_SUFFIX)
        if section_label:
            flush()
            current_section = section_label
            current_activity = None
            continue

        activity_label = _extract_label(line, ACTIVITY_PREFIX, ACTIVITY_SUFFIX)
        if activity_label:
            flush()
            current_activity = activity_label
            continue

        if line.startswith("http"):
            urls.append(line)
            if buffer:
                buffer[-1] = f"{buffer[-1]} {line}"
            else:
                buffer.append(line)
            continue

        buffer.append(line)
        if URL_PATTERN.search(line):
            urls.append(line)

    flush()
    return chunks


def _aggregate_transcript(
    timestamps: List[Dict[str, object]],
    window_seconds: float = 60.0,
    overlap_ratio: float = 0.2,
) -> List[Dict[str, object]]:
    if not timestamps:
        return []
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive.")
    if not 0 <= overlap_ratio < 1:
        raise ValueError("overlap_ratio must be in [0, 1).")

    cleaned: List[Dict[str, object]] = []
    for entry in timestamps:
        if not isinstance(entry, dict):
            continue
        start = entry.get("start")
        try:
            start_val = float(start)
        except (TypeError, ValueError):
            continue
        text = str(entry.get("text", "")).strip()
        cleaned.append({"start": start_val, "text": text})

    if not cleaned:
        return []

    aggregated: List[Dict[str, object]] = []
    idx = 0
    total = len(cleaned)
    step = window_seconds * (1 - overlap_ratio)

    while idx < total:
        start_time = float(cleaned[idx]["start"])
        end_time = start_time + window_seconds
        text_parts: List[str] = []
        scan = idx
        while scan < total and float(cleaned[scan]["start"]) < end_time:
            text = str(cleaned[scan].get("text", "")).strip()
            if text:
                text_parts.append(text)
            scan += 1

        aggregated.append(
            {
                "start": int(start_time),
                "text": _clean_join(text_parts),
            }
        )

        next_start = start_time + step
        while idx < total and float(cleaned[idx]["start"]) < next_start:
            idx += 1

    return aggregated


def parse_video_file(
    path: Path,
    course_id: str,
    download_lookup: Dict[str, Dict[str, str]],
) -> List[ParsedChunk]:
    raw = _load_json(path)
    if not isinstance(raw, list):
        logger.warning("Skipping %s: expected list payload.", path)
        return []

    chunks: List[ParsedChunk] = []
    file_origin = path.name
    chunk_counter = 0

    for entry in raw:
        if not isinstance(entry, dict):
            continue
        lecture = str(entry.get("lecture", path.stem))
        timestamps = entry.get("Timestamps") or []
        if not isinstance(timestamps, list):
            continue

        base_url = download_lookup.get(lecture, {}).get("Website") or _course_url(course_id)
        for window in _aggregate_transcript(timestamps):
            text = str(window.get("text", "")).strip()
            if not text:
                continue
            start = int(window.get("start", 0))
            separator = "&" if "?" in base_url else "?"
            url = f"{base_url}{separator}t={start}"
            chunks.append(
                ParsedChunk(
                    text=text,
                    source_type="video",
                    context_section=lecture,
                    context_activity="Transcript",
                    url=url,
                    file_origin=file_origin,
                    course_id=course_id,
                    chunk_index=chunk_counter,
                    timestamp=start,
                )
            )
            chunk_counter += 1

    return chunks


def _format_embedding_text(chunk: ParsedChunk) -> str:
    if chunk.source_type == "video":
        body = (
            f"Video Type: Lecture | Topic: {chunk.context_section} | "
            f"Transcript: {chunk.text}"
        )
    else:
        body = (
            f"Section: {chunk.context_section} | Activity: {chunk.context_activity} | "
            f"Content: {chunk.text}"
        )
    return with_document_prefix(body)


def _make_point_id(chunk: ParsedChunk) -> str:
    base = (
        f"{chunk.source_type}|{chunk.course_id}|{chunk.file_origin}|{chunk.chunk_index}"
    )
    if chunk.timestamp is not None:
        base = f"{base}|{chunk.timestamp}"
    return str(uuid5(NAMESPACE_URL, base))


def _payload_from_chunk(chunk: ParsedChunk) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "text": chunk.text,
        "source_type": chunk.source_type,
        "context_section": chunk.context_section,
        "context_activity": chunk.context_activity,
        "url": chunk.url,
        "file_origin": chunk.file_origin,
        "course_id": chunk.course_id,
        "chunk_index": chunk.chunk_index,
    }
    if chunk.timestamp is not None:
        payload["timestamp"] = chunk.timestamp
    return payload


def _load_download_log(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    raw = _load_json(path)
    if not isinstance(raw, list):
        return {}
    lookup: Dict[str, Dict[str, str]] = {}
    for entry in raw:
        if isinstance(entry, dict) and "Title" in entry:
            lookup[str(entry["Title"])] = {k: str(v) for k, v in entry.items()}
    return lookup


def _iter_course_info_files(data_root: Path, course_id: Optional[str]) -> Iterable[Path]:
    base = data_root / "isis" / "course_infos"
    if not base.exists():
        return []
    course_dirs = [base / course_id] if course_id else sorted(base.iterdir())
    files: List[Path] = []
    for course_dir in course_dirs:
        if not course_dir.is_dir():
            continue
        files.extend(sorted(course_dir.glob("*_course_infos.json")))
    return files


def _iter_video_files(data_root: Path, course_id: Optional[str]) -> Iterable[Path]:
    base = data_root / "isis" / "videos"
    if not base.exists():
        return []
    course_dirs = [base / course_id] if course_id else sorted(base.iterdir())
    files: List[Path] = []
    for course_dir in course_dirs:
        if not course_dir.is_dir():
            continue
        files.extend(sorted(course_dir.glob("*_course_video.json")))
    return files


def _resolve_course_id(path: Path) -> str:
    return path.parent.name


def build_chunks(data_root: Path, course_id: Optional[str]) -> List[ParsedChunk]:
    download_lookup = _load_download_log(data_root / "isis" / "meta" / "download_log.json")
    chunks: List[ParsedChunk] = []

    for path in _iter_course_info_files(data_root, course_id):
        course = _resolve_course_id(path)
        chunks.extend(parse_course_info_file(path, course))

    for path in _iter_video_files(data_root, course_id):
        course = _resolve_course_id(path)
        chunks.extend(parse_video_file(path, course, download_lookup))

    return chunks


def _resolve_qdrant_config(config: Optional[Config]) -> Dict[str, Optional[str]]:
    url = os.environ.get("QDRANT_URL")
    api_key = os.environ.get("QDRANT_API_KEY")
    collection = os.environ.get("QDRANT_COLLECTION")

    if config and config.qdrant:
        url = url or config.qdrant.url
        api_key = api_key or config.qdrant.api_key
        collection = collection or config.qdrant.collection

    return {"url": url, "api_key": api_key, "collection": collection}


def ingest(
    data_root: Path,
    config: Optional[Config],
    course_id: Optional[str],
    dry_run: bool = False,
) -> None:
    chunks = build_chunks(data_root, course_id)
    logger.info("Prepared %d chunks for ingestion.", len(chunks))

    if dry_run or not chunks:
        return

    qdrant_cfg = _resolve_qdrant_config(config)
    if not qdrant_cfg["url"] or not qdrant_cfg["collection"]:
        raise ValueError("Missing Qdrant url/collection; set config.yaml or env vars.")

    model = (
        config.embeddings.model
        if config and config.embeddings
        else "nomic-embed-text:v1.5"
    )
    host = config.embeddings.host if config and config.embeddings else None

    embed_client = OllamaEmbeddingClient(model=model, host=host)
    embeddings: List[List[float]] = []

    try:
        from tqdm import tqdm  # type: ignore[import]
    except ImportError:  # pragma: no cover - tqdm is in requirements
        tqdm = lambda x, **kwargs: x

    embedding_texts = [_format_embedding_text(chunk) for chunk in chunks]
    for text in tqdm(embedding_texts, desc="Embedding"):
        embeddings.append(embed_client.embed(text))

    vector_size = len(embeddings[0]) if embeddings else 0
    store = QdrantStore(
        url=qdrant_cfg["url"],
        api_key=qdrant_cfg["api_key"],
        collection_name=qdrant_cfg["collection"],
        prefer_grpc=bool(getattr(config.qdrant, "prefer_grpc", False)) if config else False,
    )
    store.ensure_collection(vector_size)

    points = []
    if len(chunks) != len(embeddings):
        raise ValueError("Embedding count mismatch; refusing to upsert.")
    for chunk, vector in zip(chunks, embeddings):
        points.append(
            PointStruct(
                id=_make_point_id(chunk),
                vector=vector,
                payload=_payload_from_chunk(chunk),
            )
        )

    store.upsert(points)
    logger.info("Upserted %d points into Qdrant.", len(points))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest ISIS crawler data into Qdrant.")
    parser.add_argument(
        "--data-root",
        default="rag/crawler/data",
        help="Root directory containing crawler outputs.",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config YAML (for Qdrant + Ollama settings).",
    )
    parser.add_argument(
        "--course-id",
        default=None,
        help="Optional course ID filter (e.g., 43321).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and chunk without embedding or uploading.",
    )
    args = parser.parse_args()

    setup_logging()
    config_path = Path(args.config)
    config = Config.load(config_path) if config_path.exists() else None

    ingest(Path(args.data_root), config, args.course_id, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
