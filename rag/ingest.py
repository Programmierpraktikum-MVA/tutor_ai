from __future__ import annotations

import argparse
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from uuid import NAMESPACE_URL, uuid5

from qdrant_client.http.models import PointStruct

try:  # qdrant-client >= 1.7
    from qdrant_client.http.models import SparseVector
except Exception:  # pragma: no cover - optional
    SparseVector = None

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

TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
HTML_EXTENSIONS = {".html", ".htm"}
PDF_EXTENSIONS = {".pdf"}


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


def _safe_join(parts: List[str]) -> str:
    return "\n".join(part.strip() for part in parts if part and part.strip()).strip()


def parse_activity_file(path: Path, course_id: str) -> List[ParsedChunk]:
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
        title = str(entry.get("title") or entry.get("modname") or "Activity")
        modname = str(entry.get("modname") or "activity")
        url = str(entry.get("url") or _course_url(course_id))
        text_parts: List[str] = []

        base_text = str(entry.get("text") or "").strip()
        if base_text:
            text_parts.append(base_text)

        chapters = entry.get("chapters") or []
        if isinstance(chapters, list):
            for chapter in chapters:
                if not isinstance(chapter, dict):
                    continue
                chapter_title = str(chapter.get("title") or "Chapter")
                chapter_text = str(chapter.get("text") or "").strip()
                if chapter_text:
                    text_parts.append(f"{chapter_title}: {chapter_text}")

        external_urls = entry.get("external_urls") or []
        if isinstance(external_urls, list) and external_urls:
            text_parts.append("External URLs: " + ", ".join(map(str, external_urls)))

        downloaded_files = entry.get("downloaded_files") or []
        if isinstance(downloaded_files, list) and downloaded_files:
            text_parts.append("Files: " + ", ".join(map(str, downloaded_files)))

        text = _safe_join(text_parts)
        if not text:
            continue
        for part in chunk_text(text):
            chunks.append(
                ParsedChunk(
                    text=part,
                    source_type="activity",
                    context_section=title,
                    context_activity=modname,
                    url=url,
                    file_origin=file_origin,
                    course_id=course_id,
                    chunk_index=chunk_counter,
                )
            )
            chunk_counter += 1

    return chunks


def parse_forum_file(path: Path, fallback_course_id: Optional[str] = None) -> List[ParsedChunk]:
    raw = _load_json(path)
    if not isinstance(raw, list):
        logger.warning("Skipping %s: expected list payload.", path)
        return []

    chunks: List[ParsedChunk] = []
    file_origin = path.name
    chunk_counter = 0

    for course_entry in raw:
        if not isinstance(course_entry, dict):
            continue
        course_id = str(course_entry.get("Course_id") or fallback_course_id or "")
        forums = course_entry.get("Forums") or []
        if not isinstance(forums, list):
            continue
        for forum in forums:
            if not isinstance(forum, dict):
                continue
            forum_name = str(forum.get("Forum_name") or "Forum")
            discussions = forum.get("Discussions") or []
            if not isinstance(discussions, list):
                continue
            for discussion in discussions:
                if not isinstance(discussion, dict):
                    continue
                discussion_name = str(discussion.get("Discussion_Name") or "Discussion")
                discussion_id = discussion.get("Discussion_Id")
                if discussion_id:
                    url = f"https://isis.tu-berlin.de/mod/forum/discuss.php?d={discussion_id}"
                else:
                    url = _course_url(course_id) if course_id else ""
                messages = discussion.get("Messages") or []
                if not isinstance(messages, list):
                    continue
                for message in messages:
                    if not isinstance(message, dict):
                        continue
                    content = str(message.get("Content") or "").strip()
                    if not content:
                        continue
                    author = str(message.get("Author") or "").strip()
                    timestamp = str(message.get("DateTime") or "").strip()
                    header = " | ".join([part for part in [author, timestamp] if part])
                    text = f"{header}: {content}" if header else content
                    for part in chunk_text(text):
                        chunks.append(
                            ParsedChunk(
                                text=part,
                                source_type="forum",
                                context_section=forum_name,
                                context_activity=discussion_name,
                                url=url,
                                file_origin=file_origin,
                                course_id=course_id,
                                chunk_index=chunk_counter,
                            )
                        )
                        chunk_counter += 1

    return chunks


def _extract_pdf_text(path: Path) -> str:
    try:
        import fitz  # type: ignore[import]
    except Exception:
        logger.warning("PyMuPDF not installed; skipping PDF %s", path)
        return ""
    try:
        doc = fitz.open(path)
    except Exception as exc:
        logger.warning("Failed to open PDF %s: %s", path, exc)
        return ""
    texts: List[str] = []
    try:
        for page in doc:
            page_text = page.get_text()
            if page_text:
                texts.append(page_text)
    finally:
        doc.close()
    return "\n".join(texts)


def _extract_html_text(raw_html: str) -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore[import]
    except Exception:
        return re.sub(r"<[^>]+>", " ", raw_html)
    soup = BeautifulSoup(raw_html, "lxml")
    return soup.get_text(" ", strip=True)


def parse_downloaded_file(path: Path, course_id: str, file_origin: str) -> List[ParsedChunk]:
    ext = path.suffix.lower()
    if ext in PDF_EXTENSIONS:
        text = _extract_pdf_text(path)
    elif ext in TEXT_EXTENSIONS:
        text = path.read_text(encoding="utf-8", errors="ignore")
    elif ext in HTML_EXTENSIONS:
        raw_html = path.read_text(encoding="utf-8", errors="ignore")
        text = _extract_html_text(raw_html)
    else:
        return []

    text = text.strip()
    if not text:
        return []

    chunks: List[ParsedChunk] = []
    chunk_counter = 0
    context_section = f"File: {path.name}"
    context_activity = "Downloaded file"
    url = _course_url(course_id) if course_id else ""

    for part in chunk_text(text):
        chunks.append(
            ParsedChunk(
                text=part,
                source_type="file",
                context_section=context_section,
                context_activity=context_activity,
                url=url,
                file_origin=file_origin,
                course_id=course_id,
                chunk_index=chunk_counter,
            )
        )
        chunk_counter += 1

    return chunks


def _format_body(chunk: ParsedChunk) -> str:
    if chunk.source_type == "video":
        return (
            f"Video Type: Lecture | Topic: {chunk.context_section} | "
            f"Transcript: {chunk.text}"
        )
    return (
        f"Section: {chunk.context_section} | Activity: {chunk.context_activity} | "
        f"Content: {chunk.text}"
    )


def _format_embedding_text(chunk: ParsedChunk) -> str:
    return with_document_prefix(_format_body(chunk))


def _format_sparse_text(chunk: ParsedChunk) -> str:
    return _format_body(chunk)


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


def _build_sparse_embeddings(texts: List[str], model_name: str) -> List[object]:
    try:
        from fastembed import SparseTextEmbedding  # type: ignore[import]
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("fastembed is required for sparse embeddings.") from exc

    model = SparseTextEmbedding(model_name=model_name)
    return list(model.embed(texts))


def _to_sparse_vector(sparse_embedding: object) -> object:
    indices = getattr(sparse_embedding, "indices", None)
    values = getattr(sparse_embedding, "values", None)
    if indices is None or values is None:
        raise ValueError("Invalid sparse embedding; missing indices/values.")
    if SparseVector is not None:
        return SparseVector(indices=list(indices), values=list(values))
    return {"indices": list(indices), "values": list(values)}


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


def _iter_resource_files(data_root: Path, course_id: Optional[str]) -> Iterable[Path]:
    base = data_root / "isis" / "resources"
    if not base.exists():
        return []
    course_dirs = [base / course_id] if course_id else sorted(base.iterdir())
    files: List[Path] = []
    for course_dir in course_dirs:
        if not course_dir.is_dir():
            continue
        candidate = course_dir / "activities.json"
        if candidate.exists():
            files.append(candidate)
    return files


def _iter_forum_files(data_root: Path, course_id: Optional[str]) -> Iterable[Path]:
    base = data_root / "isis" / "forums" / "course_forum_data"
    if not base.exists():
        return []
    if course_id:
        candidate = base / f"course_{course_id}.json"
        return [candidate] if candidate.exists() else []
    return sorted(base.glob("course_*.json"))


def _iter_downloaded_files(data_root: Path, course_id: Optional[str]) -> Iterable[Path]:
    base = data_root / "isis" / "files"
    if not base.exists():
        return []
    if course_id:
        roots = [base / course_id]
    else:
        roots = [p for p in base.iterdir() if p.is_dir() and p.name != "_downloads"]
    files: List[Path] = []
    allowed_exts = TEXT_EXTENSIONS | HTML_EXTENSIONS | PDF_EXTENSIONS
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in allowed_exts:
                files.append(path)
    return files


def _resolve_course_id_from_files_path(data_root: Path, path: Path) -> str:
    try:
        rel = path.relative_to(data_root)
    except ValueError:
        return ""
    parts = list(rel.parts)
    if "files" in parts:
        idx = parts.index("files")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return ""


def _relative_origin(data_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(data_root))
    except ValueError:
        return path.name


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

    for path in _iter_resource_files(data_root, course_id):
        course = _resolve_course_id(path)
        chunks.extend(parse_activity_file(path, course))

    for path in _iter_forum_files(data_root, course_id):
        chunks.extend(parse_forum_file(path, course_id))

    for path in _iter_downloaded_files(data_root, course_id):
        course = _resolve_course_id_from_files_path(data_root, path)
        file_origin = _relative_origin(data_root, path)
        chunks.extend(parse_downloaded_file(path, course, file_origin))

    return chunks


def _resolve_qdrant_config(config: Optional[Config]) -> Dict[str, Optional[str]]:
    url = os.environ.get("QDRANT_URL")
    api_key = os.environ.get("QDRANT_API_KEY")
    collection = os.environ.get("QDRANT_COLLECTION")
    dense_vector_name = os.environ.get("QDRANT_DENSE_VECTOR")
    sparse_vector_name = os.environ.get("QDRANT_SPARSE_VECTOR")
    use_sparse_env = os.environ.get("QDRANT_USE_SPARSE")

    if config and config.qdrant:
        url = url or config.qdrant.url
        api_key = api_key or config.qdrant.api_key
        collection = collection or config.qdrant.collection
        dense_vector_name = dense_vector_name or config.qdrant.dense_vector_name
        sparse_vector_name = sparse_vector_name or config.qdrant.sparse_vector_name
        if use_sparse_env is None:
            use_sparse_env = "1" if config.qdrant.use_sparse else "0"

    return {
        "url": url,
        "api_key": api_key,
        "collection": collection,
        "dense_vector_name": dense_vector_name,
        "sparse_vector_name": sparse_vector_name,
        "use_sparse": use_sparse_env,
    }


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

    dense_vector_name = qdrant_cfg["dense_vector_name"] or "dense-text-vector"
    sparse_vector_name = qdrant_cfg["sparse_vector_name"] or "sparse-text-vector"
    use_sparse = str(qdrant_cfg.get("use_sparse") or "").lower() not in {"0", "false", "no"}

    model = (
        config.embeddings.model
        if config and config.embeddings
        else "nomic-embed-text:v1.5"
    )
    host = config.embeddings.host if config and config.embeddings else None
    sparse_model = (
        config.embeddings.sparse_model
        if config and config.embeddings
        else "Qdrant/bm25"
    )

    embed_client = OllamaEmbeddingClient(model=model, host=host)
    embeddings: List[List[float]] = []
    sparse_embeddings: List[object] = []

    try:
        from tqdm import tqdm  # type: ignore[import]
    except ImportError:  # pragma: no cover - tqdm is in requirements
        tqdm = lambda x, **kwargs: x

    embedding_texts = [_format_embedding_text(chunk) for chunk in chunks]
    for text in tqdm(embedding_texts, desc="Embedding"):
        embeddings.append(embed_client.embed(text))

    if use_sparse:
        sparse_texts = [_format_sparse_text(chunk) for chunk in chunks]
        sparse_embeddings = _build_sparse_embeddings(sparse_texts, sparse_model)

    vector_size = len(embeddings[0]) if embeddings else 0
    store = QdrantStore(
        url=qdrant_cfg["url"],
        api_key=qdrant_cfg["api_key"],
        collection_name=qdrant_cfg["collection"],
        prefer_grpc=bool(getattr(config.qdrant, "prefer_grpc", False)) if config else False,
    )
    store.ensure_collection(
        vector_size,
        dense_vector_name=dense_vector_name,
        sparse_vector_name=sparse_vector_name,
        use_sparse=use_sparse,
    )

    points = []
    if len(chunks) != len(embeddings):
        raise ValueError("Embedding count mismatch; refusing to upsert.")
    if use_sparse and len(chunks) != len(sparse_embeddings):
        raise ValueError("Sparse embedding count mismatch; refusing to upsert.")
    for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        dense_vector = vector
        if use_sparse:
            sparse_vector = _to_sparse_vector(sparse_embeddings[idx])
            payload_vector = {
                dense_vector_name: dense_vector,
                sparse_vector_name: sparse_vector,
            }
        else:
            payload_vector = {dense_vector_name: dense_vector}
        points.append(
            PointStruct(
                id=_make_point_id(chunk),
                vector=payload_vector,
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
