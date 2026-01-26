
# Tutor AI

Tutor AI provides a Matrix chatbot backed by local Ollama models and a minimal
RAG pipeline that crawls ISIS/MOSES data, embeds it, and stores vectors in
Qdrant.

## Features (current)

- Matrix chatbot (no RAG): Matrix text → local Ollama (`gemma3:12b` by default)
- Commands: `!help`, `!status`
- RAG ingestion pipeline (ISIS): parse → chunk → embed (Ollama) → upsert to Qdrant
- Selenium crawler for ISIS/MOSES data (writes JSON to `rag/crawler/data`)

## Prerequisites

- Python 3.8–3.11, pip, virtualenv
- Ollama installed locally
- Matrix account + access token (for the bot)
- Qdrant instance reachable from this machine (for ingestion)
- ffmpeg (required for the crawler)

## Setup (single environment)

1) Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   ```
2) Install dependencies (choose one):
   CPU:
   ```bash
   pip install -r requirements-all-cpu.txt
   ```
   CUDA (12.1):
   ```bash
   pip install -r requirements-all-cu121.txt
   ```
   Hinweis: nutze die gleiche CPU/CUDA-Variante fuer alle Requirements, um Konflikte zu vermeiden.
3) Install ffmpeg:
   ```bash
   sudo apt install ffmpeg
   ```
4) Copy `config.example.yaml` to `config.yaml` and fill in Matrix credentials and room IDs.
5) Start Ollama and pull the required models:
   ```bash
   ollama serve
   ollama pull gemma3:12b
   ollama pull nomic-embed-text:v1.5
   ```

## Configuration (Ollama, embeddings, Qdrant)

`config.yaml` supports:

```yaml
ollama:
  model: "gemma3:12b"
  host: "http://localhost:11434"

embeddings:
  model: "nomic-embed-text:v1.5"
  host: "http://localhost:11434"

qdrant:
  url: "http://localhost:6333"
  api_key: "REPLACE_ME"
  collection: "tutor_ai"
  prefer_grpc: false
```

Qdrant environment overrides: `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`.

## Usage

Start Ollama if it is not running:

```bash
ollama serve
```

Bot (Matrix):

```bash
. .venv/bin/activate
python3 -m bot.main
```

Crawler (ISIS/MOSES):

```bash
python3 rag/crawler/selenium/main.py <username> <password>
```

Optional environment variables: `CRAWLER_DATA_DIR`, `ISIS_COURSE_ID`, `WHISPER_DEVICE`.
Output data is written to `rag/crawler/data` by default (override with `CRAWLER_DATA_DIR`).

Ingestion (Qdrant):

```bash
python3 -m rag.ingest --data-root rag/crawler/data --config config.yaml
```

Optional flags:

```bash
python3 -m rag.ingest --course-id 43321
python3 -m rag.ingest --dry-run
```

Clear crawler output:

```bash
rm -rf rag/crawler/data/*
```

If you set `CRAWLER_DATA_DIR`, clear that directory instead:

```bash
rm -rf "${CRAWLER_DATA_DIR:?}"/*
```

## Scheduling

Use a cron/systemd timer to run the crawler and ingestion script regularly.
An example helper is provided at `scripts/run_crawl_and_ingest.sh` (expects
`ISIS_USERNAME`, `ISIS_PASSWORD`, and optional Qdrant env vars).

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Maximilian Hans - m.hans@tu-berlin.de

Project Link: [https://github.com/Programmierpraktikum-MVA/tutor_ai](https://github.com/Programmierpraktikum-MVA/tutor_ai)
