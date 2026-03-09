from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import NAMESPACE_URL, uuid5

from qdrant_client.http.models import PointStruct

try:  # qdrant-client >= 1.7
    from qdrant_client.http.models import SparseVector
except Exception:  # pragma: no cover - optional
    SparseVector = None

from config import Config
from db.qdrant import QdrantStore
from llm.embeddings import OllamaEmbeddingClient, with_document_prefix
from llm.ollama import OllamaVisionClient
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

FILE_CHUNK_MAX_CHARS = 1400
FILE_CHUNK_OVERLAP = 180
PDF_LINE_REPEAT_MIN_COUNT = 3
PDF_LINE_REPEAT_MIN_RATIO = 0.2
PDF_SLIDE_VISION_PROMPT_VERSION = "v1"
DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text:v1.5"
DEFAULT_SPARSE_MODEL = "Qdrant/bm25"
DEFAULT_EMBEDDING_MAX_CHARS = 1800
DEFAULT_EMBEDDING_RETRIES = 3
EMBEDDING_RETRY_SLEEP_SECONDS = 1.0
EMBEDDING_FAILURE_REPORT_NAME = "embedding_failures.json"


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
    page_number: Optional[int] = None
    page_count: Optional[int] = None
    text_transcript: Optional[str] = None
    vision_description: Optional[str] = None


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


def _normalize_extracted_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    # Remove common zero-width separators from PDF extraction.
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def _pdf_line_signature(line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    line = line.casefold()
    line = re.sub(r"\d+", "<num>", line)
    line = re.sub(r"\s+", " ", line)
    return line


def _strip_repeated_pdf_lines(pages: List[str]) -> List[str]:
    if not pages:
        return pages
    signatures: List[List[str]] = []
    for page in pages:
        page_signatures = []
        for line in page.splitlines():
            sig = _pdf_line_signature(line)
            if sig and len(sig) >= 8:
                page_signatures.append(sig)
        signatures.append(list(dict.fromkeys(page_signatures)))

    counter = Counter(sig for page_sigs in signatures for sig in page_sigs)
    page_count = len(pages)
    repeated = {
        sig
        for sig, count in counter.items()
        if count >= PDF_LINE_REPEAT_MIN_COUNT and (count / page_count) >= PDF_LINE_REPEAT_MIN_RATIO
    }
    if not repeated:
        return pages

    cleaned_pages: List[str] = []
    for page in pages:
        kept_lines = []
        for line in page.splitlines():
            sig = _pdf_line_signature(line)
            if sig in repeated:
                continue
            kept_lines.append(line)
        cleaned_pages.append("\n".join(kept_lines))
    return cleaned_pages


def _extract_pdf_pages(path: Path) -> List[str]:
    try:
        import fitz  # type: ignore[import]
    except Exception:
        logger.warning("PyMuPDF not installed; skipping PDF %s", path)
        return []
    try:
        doc = fitz.open(path)
    except Exception as exc:
        logger.warning("Failed to open PDF %s: %s", path, exc)
        return []
    texts: List[str] = []
    try:
        for page in doc:
            page_text = page.get_text("text", sort=True)
            texts.append(page_text or "")
    finally:
        doc.close()
    texts = [_normalize_extracted_text(page) for page in texts]
    return _strip_repeated_pdf_lines(texts)


def _extract_pdf_text(path: Path) -> str:
    pages = [page for page in _extract_pdf_pages(path) if page.strip()]
    return "\n\n".join(pages)


def _pdf_slide_prompt(transcript: str) -> str:
    normalized_transcript = transcript.strip()
    return (
        "Generate a high level description of the slide provided. "
        "It will be used to enhance the parsed text of the slide.\n\n"
        "Return exactly these metadata sections:\n"
        "Main topic: <1 short phrase>\n"
        "Short description: <max 2 short phrases>\n\n"
        "Use the image as the primary source and the transcript as supporting context.\n"
        "Do not repeat the transcript verbatim unless it is necessary to clarify a label.\n\n"
        "TEXT_TRANSCRIPT:\n"
        f"{normalized_transcript}"
    )


def _combine_pdf_slide_text(vision_description: str, transcript: str) -> str:
    parts = [vision_description.strip(), "TEXT_TRANSCRIPT:"]
    cleaned_transcript = transcript.strip()
    if cleaned_transcript:
        parts.append(cleaned_transcript)
    return "\n".join(parts).strip()


def _pdf_sidecar_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.slides.json")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_pdf_slide_cache(
    cache_path: Path,
    *,
    pdf_hash: str,
    page_count: int,
    prompt_version: str,
    model_name: str,
) -> Optional[List[Dict[str, Any]]]:
    if not cache_path.exists():
        return None
    try:
        raw = _load_json(cache_path)
    except Exception as exc:
        logger.warning("Failed to read PDF slide cache %s: %s", cache_path, exc)
        return None
    if not isinstance(raw, dict):
        return None

    header = raw.get("header")
    slides = raw.get("slides")
    if not isinstance(header, dict) or not isinstance(slides, list):
        return None
    if header.get("pdf_hash") != pdf_hash:
        return None
    try:
        cached_page_count = int(header.get("page_count", -1))
    except (TypeError, ValueError):
        return None
    if cached_page_count != page_count:
        return None
    if header.get("prompt_version") != prompt_version:
        return None
    if header.get("model_name") != model_name:
        return None
    if len(slides) != page_count:
        return None

    normalized: List[Dict[str, Any]] = []
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            return None
        try:
            page_number = int(slide.get("page_number", -1))
        except (TypeError, ValueError):
            return None
        if page_number != index:
            return None
        transcript = str(slide.get("text_transcript", ""))
        vision_description = str(slide.get("vision_description", "")).strip()
        if not vision_description:
            return None
        normalized.append(
            {
                "page_number": page_number,
                "text_transcript": transcript,
                "vision_description": vision_description,
            }
        )
    return normalized


def _write_pdf_slide_cache(
    cache_path: Path,
    *,
    pdf_hash: str,
    page_count: int,
    prompt_version: str,
    model_name: str,
    slides: List[Dict[str, Any]],
) -> None:
    payload = {
        "header": {
            "pdf_hash": pdf_hash,
            "page_count": page_count,
            "prompt_version": prompt_version,
            "model_name": model_name,
        },
        "slides": slides,
    }
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _render_pdf_page_png(page: Any) -> bytes:
    try:
        import fitz  # type: ignore[import]
    except Exception as exc:
        raise RuntimeError("PyMuPDF not installed; cannot render PDF pages.") from exc
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    return pixmap.tobytes("png")


def _generate_pdf_slide_descriptions(
    path: Path,
    transcripts: List[str],
    *,
    model_name: str,
    host: Optional[str],
) -> List[Dict[str, Any]]:
    try:
        import fitz  # type: ignore[import]
    except Exception as exc:
        raise RuntimeError("PyMuPDF not installed; cannot render PDF pages.") from exc

    client = OllamaVisionClient(model=model_name, host=host)
    slides: List[Dict[str, Any]] = []
    doc = fitz.open(path)
    try:
        if len(doc) != len(transcripts):
            raise ValueError("PDF page count mismatch between text extraction and rendering.")
        for index, page in enumerate(doc, start=1):
            transcript = transcripts[index - 1].strip()
            prompt = _pdf_slide_prompt(transcript)
            image_bytes = _render_pdf_page_png(page)
            vision_description = client.generate(prompt, [image_bytes]).strip()
            if not vision_description:
                raise ValueError(f"Empty vision description for slide {index}.")
            slides.append(
                {
                    "page_number": index,
                    "text_transcript": transcript,
                    "vision_description": vision_description,
                }
            )
    finally:
        doc.close()
    return slides


def _resolve_pdf_slide_cache(
    path: Path,
    *,
    transcripts: List[str],
    model_name: str,
    host: Optional[str],
) -> List[Dict[str, Any]]:
    cache_path = _pdf_sidecar_path(path)
    pdf_hash = _hash_file(path)
    page_count = len(transcripts)
    cached = _load_pdf_slide_cache(
        cache_path,
        pdf_hash=pdf_hash,
        page_count=page_count,
        prompt_version=PDF_SLIDE_VISION_PROMPT_VERSION,
        model_name=model_name,
    )
    if cached is not None:
        return cached

    slides = _generate_pdf_slide_descriptions(
        path,
        transcripts,
        model_name=model_name,
        host=host,
    )
    _write_pdf_slide_cache(
        cache_path,
        pdf_hash=pdf_hash,
        page_count=page_count,
        prompt_version=PDF_SLIDE_VISION_PROMPT_VERSION,
        model_name=model_name,
        slides=slides,
    )
    return slides


def _extract_html_text(raw_html: str) -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore[import]
    except Exception:
        return re.sub(r"<[^>]+>", " ", raw_html)
    soup = BeautifulSoup(raw_html, "lxml")
    return soup.get_text(" ", strip=True)


def _parse_pdf_file(
    path: Path,
    course_id: str,
    file_origin: str,
    *,
    config: Optional[Config],
) -> List[ParsedChunk]:
    transcripts = _extract_pdf_pages(path)
    if not transcripts:
        return []

    model_name = config.ollama.model if config and config.ollama else DEFAULT_OLLAMA_MODEL
    host = config.ollama.host if config and config.ollama else None
    try:
        slides = _resolve_pdf_slide_cache(
            path,
            transcripts=transcripts,
            model_name=model_name,
            host=host,
        )
    except Exception as exc:
        logger.error("Skipping PDF %s after vision enrichment failure: %s", path, exc)
        return []

    page_count = len(slides)
    url = _course_url(course_id) if course_id else ""
    context_section = f"File: {path.name}"
    chunks: List[ParsedChunk] = []
    for index, slide in enumerate(slides):
        page_number = int(slide["page_number"])
        transcript = str(slide.get("text_transcript", "")).strip()
        vision_description = str(slide.get("vision_description", "")).strip()
        combined_text = _combine_pdf_slide_text(vision_description, transcript)
        chunks.append(
            ParsedChunk(
                text=combined_text,
                source_type="file",
                context_section=context_section,
                context_activity=f"Slide {page_number}",
                url=url,
                file_origin=file_origin,
                course_id=course_id,
                chunk_index=index,
                page_number=page_number,
                page_count=page_count,
                text_transcript=transcript,
                vision_description=vision_description,
            )
        )
    return chunks


def parse_downloaded_file(
    path: Path,
    course_id: str,
    file_origin: str,
    *,
    config: Optional[Config] = None,
) -> List[ParsedChunk]:
    ext = path.suffix.lower()
    if ext in PDF_EXTENSIONS:
        return _parse_pdf_file(path, course_id, file_origin, config=config)
    if ext in TEXT_EXTENSIONS:
        text = path.read_text(encoding="utf-8", errors="ignore")
    elif ext in HTML_EXTENSIONS:
        raw_html = path.read_text(encoding="utf-8", errors="ignore")
        text = _extract_html_text(raw_html)
    else:
        return []

    text = _normalize_extracted_text(text).strip()
    if not text:
        return []

    chunks: List[ParsedChunk] = []
    chunk_counter = 0
    context_section = f"File: {path.name}"
    context_activity = "Downloaded file"
    url = _course_url(course_id) if course_id else ""

    for part in chunk_text(text, max_chars=FILE_CHUNK_MAX_CHARS, overlap=FILE_CHUNK_OVERLAP):
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


def _chunk_debug_label(chunk: ParsedChunk) -> str:
    parts = [
        f"source_type={chunk.source_type}",
        f"course_id={chunk.course_id or '<none>'}",
        f"file={chunk.file_origin}",
        f"chunk_index={chunk.chunk_index}",
        f"section={chunk.context_section}",
        f"activity={chunk.context_activity}",
    ]
    if chunk.page_number is not None:
        parts.append(f"page={chunk.page_number}/{chunk.page_count}")
    if chunk.timestamp is not None:
        parts.append(f"timestamp={chunk.timestamp}")
    return " | ".join(parts)


def _truncate_embedding_input(text: str, max_chars: int) -> Tuple[str, bool]:
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False

    prefix = ""
    body = text
    if text.startswith("search_document: "):
        prefix = "search_document: "
        body = text[len(prefix) :]
    elif text.startswith("search_query: "):
        prefix = "search_query: "
        body = text[len(prefix) :]

    available = max_chars - len(prefix)
    if available <= 0:
        return text[:max_chars], True

    truncated_body = body[:available]
    cut = truncated_body.rfind(" ")
    if cut >= max(int(available * 0.7), 1):
        truncated_body = truncated_body[:cut]
    return prefix + truncated_body.rstrip(), True


def _embedding_failure_payload(
    chunk: ParsedChunk,
    *,
    error: str,
    embedding_chars: int,
) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "error": error,
        "embedding_chars": embedding_chars,
        "source_type": chunk.source_type,
        "course_id": chunk.course_id,
        "file_origin": chunk.file_origin,
        "context_section": chunk.context_section,
        "context_activity": chunk.context_activity,
        "chunk_index": chunk.chunk_index,
        "url": chunk.url,
    }
    if chunk.page_number is not None:
        payload["page_number"] = chunk.page_number
        payload["page_count"] = chunk.page_count
    if chunk.timestamp is not None:
        payload["timestamp"] = chunk.timestamp
    return payload


def _embedding_failure_report_path(data_root: Path) -> Path:
    return data_root / "isis" / "meta" / EMBEDDING_FAILURE_REPORT_NAME


def _write_embedding_failure_report(data_root: Path, failures: List[Dict[str, object]]) -> Optional[Path]:
    if not failures:
        return None
    path = _embedding_failure_report_path(data_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(failures, handle, ensure_ascii=False, indent=2)
    return path


def _resolve_embedding_max_chars() -> int:
    raw = os.environ.get("EMBEDDING_MAX_CHARS")
    if not raw:
        return DEFAULT_EMBEDDING_MAX_CHARS
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "Invalid EMBEDDING_MAX_CHARS=%r; falling back to %d.",
            raw,
            DEFAULT_EMBEDDING_MAX_CHARS,
        )
        return DEFAULT_EMBEDDING_MAX_CHARS
    return max(200, value)


def _resolve_embedding_retries() -> int:
    raw = os.environ.get("EMBEDDING_RETRIES")
    if not raw:
        return DEFAULT_EMBEDDING_RETRIES
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "Invalid EMBEDDING_RETRIES=%r; falling back to %d.",
            raw,
            DEFAULT_EMBEDDING_RETRIES,
        )
        return DEFAULT_EMBEDDING_RETRIES
    return max(1, value)


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
    if chunk.page_number is not None:
        payload["page_number"] = chunk.page_number
    if chunk.page_count is not None:
        payload["page_count"] = chunk.page_count
    if chunk.text_transcript is not None:
        payload["text_transcript"] = chunk.text_transcript
    if chunk.vision_description is not None:
        payload["vision_description"] = chunk.vision_description
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


def build_chunks(
    data_root: Path,
    course_id: Optional[str],
    config: Optional[Config] = None,
) -> List[ParsedChunk]:
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
        chunks.extend(parse_downloaded_file(path, course, file_origin, config=config))

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
    chunks = build_chunks(data_root, course_id, config=config)
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
        else DEFAULT_EMBEDDING_MODEL
    )
    host = config.embeddings.host if config and config.embeddings else None
    sparse_model = (
        config.embeddings.sparse_model
        if config and config.embeddings
        else DEFAULT_SPARSE_MODEL
    )

    embed_client = OllamaEmbeddingClient(model=model, host=host)
    embeddings: List[List[float]] = []
    sparse_embeddings: List[object] = []
    embedded_chunks: List[ParsedChunk] = []
    failed_embedding_chunks: List[Dict[str, object]] = []
    embedding_max_chars = _resolve_embedding_max_chars()
    embedding_retries = _resolve_embedding_retries()

    try:
        from tqdm import tqdm  # type: ignore[import]
    except ImportError:  # pragma: no cover - tqdm is in requirements
        tqdm = lambda x, **kwargs: x

    for chunk in tqdm(chunks, desc="Embedding"):
        raw_text = _format_embedding_text(chunk)
        text, truncated = _truncate_embedding_input(raw_text, embedding_max_chars)
        if truncated:
            logger.warning(
                "Truncated embedding input from %d to %d chars for %s",
                len(raw_text),
                len(text),
                _chunk_debug_label(chunk),
            )

        logger.debug(
            "Embedding chunk: %s | embedding_chars=%d",
            _chunk_debug_label(chunk),
            len(text),
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, embedding_retries + 1):
            try:
                embeddings.append(embed_client.embed(text))
                embedded_chunks.append(chunk)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt < embedding_retries:
                    logger.warning(
                        "Embedding failed (attempt %d/%d) for %s | embedding_chars=%d | error=%s",
                        attempt,
                        embedding_retries,
                        _chunk_debug_label(chunk),
                        len(text),
                        exc,
                    )
                    time.sleep(EMBEDDING_RETRY_SLEEP_SECONDS)
                    continue
                logger.error(
                    "Skipping chunk after embedding failure for %s | embedding_chars=%d | error=%s",
                    _chunk_debug_label(chunk),
                    len(text),
                    exc,
                )
                failed_embedding_chunks.append(
                    _embedding_failure_payload(
                        chunk,
                        error=str(exc),
                        embedding_chars=len(text),
                    )
                )
        if last_error is not None:
            continue

    if len(embedded_chunks) != len(chunks):
        report_path = _write_embedding_failure_report(data_root, failed_embedding_chunks)
        logger.warning(
            "Embedded %d/%d chunks successfully; skipped %d failed chunk(s).",
            len(embedded_chunks),
            len(chunks),
            len(chunks) - len(embedded_chunks),
        )
        for failure in failed_embedding_chunks:
            logger.warning(
                "Skipped chunk: file=%s | chunk_index=%s | section=%s | activity=%s | error=%s",
                failure.get("file_origin"),
                failure.get("chunk_index"),
                failure.get("context_section"),
                failure.get("context_activity"),
                failure.get("error"),
            )
        if report_path is not None:
            logger.warning("Wrote embedding failure report to %s", report_path)
    chunks = embedded_chunks

    if not chunks:
        logger.warning("No chunks embedded successfully; aborting upsert.")
        return

    if use_sparse:
        sparse_texts = [_format_sparse_text(chunk) for chunk in chunks]
        try:
            sparse_embeddings = _build_sparse_embeddings(sparse_texts, sparse_model)
        except RuntimeError as exc:
            logger.warning(
                "Sparse embeddings unavailable (%s); continuing with dense-only upsert.",
                exc,
            )
            use_sparse = False
            sparse_embeddings = []

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
