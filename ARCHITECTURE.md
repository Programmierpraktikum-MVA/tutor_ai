# Tutor AI Architecture (Current)

## Overview

This repo contains a Matrix bot that uses local Ollama for generation and a
minimal RAG ingestion pipeline that parses ISIS crawler output, embeds it, and
stores vectors in Qdrant. Retrieval is not wired yet.

## High-level flow

Crawler (Selenium) -> JSON files in `rag/crawler/data` -> `rag/ingest.py`
-> parsing + cleaning -> chunking -> embedding text formatting -> embeddings
(Ollama) -> Qdrant collection.

Matrix messages -> `bot/matrix_io.py` -> `bot/router.py` -> `bot/handlers.py`
-> `llm/ollama.py` for generation.

## Components

### Crawler output
- Location: `rag/crawler/data`
- ISIS course info: `rag/crawler/data/isis/course_infos/<course_id>/*_course_infos.json`
- ISIS videos: `rag/crawler/data/isis/videos/<course_id>/*_course_video.json`
- Video metadata: `rag/crawler/data/isis/meta/download_log.json`
- Convenience script: `scripts/run_crawl_and_ingest.sh`

### Ingestion
- Entry point: `rag/ingest.py`
- Parsing:
  - Course infos: state machine over "Abschnitt" and "Aktivität"
  - Videos: 60s windows with 20% overlap
- Chunking: `rag/chunkers.py` (character-based, overlap)
- Embeddings: `llm/embeddings.py` (Ollama `nomic-embed-text:v1.5`)
- Vector store: `db/qdrant.py` (create collection, upsert points)

Payload schema (stored in Qdrant):
- `text`, `source_type`, `context_section`, `context_activity`, `url`,
  `timestamp` (videos), `file_origin`, `course_id`, `chunk_index`

### LLM generation
- `llm/ollama.py` wraps Ollama chat for Matrix replies.

## Detailed data preparation (ingestion)

### Input discovery
- `rag/ingest.py` searches under `rag/crawler/data/isis` for:
  - Course info files: `course_infos/<course_id>/*_course_infos.json`
  - Video files: `videos/<course_id>/*_course_video.json`
- Optional `--course-id` limits ingestion to a single course folder.
- `rag/crawler/data/isis/meta/download_log.json` is read (if present) to map
  video lecture titles to a base "Website" URL.

### Course info parsing (course_infos JSON)
- Each JSON file is expected to be a list of strings (lines scraped from ISIS).
- A lightweight state machine tracks `current_section` and `current_activity`:
  - A line like `Abschnitt X auswählen` sets the section and flushes the buffer.
  - A line like `Aktivität Y auswählen` sets the activity and flushes the buffer.
- Noise lines are ignored (`Einklappen`, `Ausklappen`, etc.).
- URLs are detected by regex; the first URL in a block becomes the chunk URL.
- The remaining lines are concatenated with `_clean_join`, which:
  - Collapses whitespace to single spaces.
  - Removes spaces before punctuation like `, . ; :`.
- Each block becomes one or more chunks via `chunk_text` (see below). Each chunk
  inherits the section/activity context and the derived URL.

### Video parsing (videos JSON)
- Each JSON file is expected to be a list of dicts with:
  - `lecture` (optional label; fallback is the filename stem)
  - `Timestamps`: list of `{start, text}` items from the transcript.
- `_aggregate_transcript` builds sliding windows over the timestamps:
  - `window_seconds=60`, `overlap_ratio=0.2` (step size = 48s).
  - Window start is the first timestamp in the window.
  - All transcript snippets with `start < window_end` are concatenated.
- For each window:
  - The URL is the lecture's base URL with `?t=<start>` or `&t=<start>`.
  - `context_section` is the lecture title; `context_activity` is `"Transcript"`.

### Chunking (`rag/chunkers.py`)
- `chunk_text(text, max_chars=2000, overlap=200)`:
  - Normalizes whitespace (`" ".join(text.split())`).
  - If short enough, returns a single chunk.
  - Otherwise it scans backwards from `max_chars` to find a whitespace break,
    but never earlier than 60% of `max_chars`.
  - The next chunk starts `overlap` characters before the cut.

### Chunk metadata
- Every parsed chunk is represented by `ParsedChunk`, which includes:
  `text`, `source_type`, `context_section`, `context_activity`, `url`,
  `file_origin`, `course_id`, `chunk_index`, and `timestamp` (videos only).
- Stable IDs for Qdrant are built with UUIDv5 over these fields so re-ingests
  upsert the same point IDs.

## Embedding generation details

### Embedding text formatting
- Each chunk is converted to a model-specific text string:
  - Course info:
    `Section: <section> | Activity: <activity> | Content: <text>`
  - Video:
    `Video Type: Lecture | Topic: <lecture> | Transcript: <text>`
- `llm/embeddings.with_document_prefix` prepends:
  `search_document: ` (as required by `nomic-embed-text`).

### Embedding execution (Ollama)
- `OllamaEmbeddingClient` sends one text at a time via
  `ollama.Client.embeddings(model=<model>, prompt=<text>)`.
- There is no batching in the current implementation.
- The default model is `nomic-embed-text:v1.5`, overridable in `config.yaml`
  under `embeddings.model`.
- The embeddings host is `embeddings.host`, falling back to `ollama.host`.

### Qdrant storage
- Vector size is derived from the first embedding vector.
- `QdrantStore.ensure_collection` creates the collection if it doesn't exist
  (distance = cosine).
- Payload stored per point:
  `text`, `source_type`, `context_section`, `context_activity`, `url`,
  `file_origin`, `course_id`, `chunk_index`, and optional `timestamp`.

### Query embeddings (future retrieval)
- `llm/embeddings.with_query_prefix` exists for query embedding strings:
  `search_query: <user query>`, but retrieval is not implemented yet.

## Configuration

Configured in `config.yaml` via `config.py`:
- `ollama` for chat model
- `embeddings` for embedding model + host
- `qdrant` for URL, API key, collection name

Environment overrides:
- `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`

## Current limitations / TODO

- Retrieval layer is not implemented (`rag/retrieve.py` is TODO).
- Bot is not yet using Qdrant results in responses.
