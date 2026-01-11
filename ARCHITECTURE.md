# Tutor AI Architecture (Current)

## Overview

This repo contains a Matrix bot that uses local Ollama for generation and a
minimal RAG ingestion pipeline that parses ISIS crawler output, embeds it, and
stores vectors in Qdrant. Retrieval is not wired yet.

## High-level flow

Crawler (Selenium) -> JSON files in `rag/crawler/data` -> `rag/ingest.py`
-> chunking -> embeddings (Ollama) -> Qdrant collection.

Matrix messages -> `bot/handlers.py` -> `llm/ollama.py` for generation.

## Components

### Crawler output
- Location: `rag/crawler/data`
- ISIS course info: `rag/crawler/data/isis/course_infos/<course_id>/*_course_infos.json`
- ISIS videos: `rag/crawler/data/isis/videos/<course_id>/*_course_video.json`
- Video metadata: `rag/crawler/data/isis/meta/download_log.json`

### Ingestion
- Entry point: `rag/ingest.py`
- Parsing:
  - Course infos: state machine over "Abschnitt" and "Aktivitaet"
  - Videos: 60s windows with 20% overlap
- Chunking: `rag/chunkers.py` (character-based, overlap)
- Embeddings: `llm/embeddings.py` (Ollama `nomic-embed-text:v1.5`)
- Vector store: `db/qdrant.py` (create collection, upsert points)

Payload schema (stored in Qdrant):
- `text`, `source_type`, `context_section`, `context_activity`, `url`,
  `timestamp` (videos), `file_origin`, `course_id`, `chunk_index`

### LLM generation
- `llm/ollama.py` wraps Ollama chat for Matrix replies.

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
