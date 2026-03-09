
# Tutor AI

Tutor AI provides a Matrix chatbot backed by local Ollama models and a minimal
RAG pipeline that crawls ISIS/MOSES data, embeds it, and stores vectors in
Qdrant.

## Features (current)

- Matrix chatbot (no RAG): Matrix text → local Ollama (`gemma3:12b` by default)
- Commands: `!help`, `!status`
- Hybrid RAG ingestion pipeline (ISIS): parse → chunk → dense+ sparse embeddings → upsert to Qdrant
- PDF slide enrichment: ISIS PDFs are ingested per page, enriched with the local multimodal Ollama model, and cached in `*.pdf.slides.json`
- Selenium crawler for ISIS/MOSES data (writes JSON to `rag/crawler/data`)
- Interactive RAG probe script (retrieval-only, no LLM): `scripts/rag_probe.py`

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
   Hinweis: the `ollama.model` used for chat is also used during PDF ingestion, so it must support images.

## Configuration (Ollama, embeddings, Qdrant)

`config.yaml` supports:

```yaml
ollama:
  model: "gemma3:12b"
  host: "http://localhost:11434"

embeddings:
  model: "nomic-embed-text:v1.5"
  host: "http://localhost:11434"
  sparse_model: "Qdrant/bm25"

qdrant:
  url: "http://localhost:6333"
  api_key: "REPLACE_ME"
  collection: "tutor_ai_hybrid"
  prefer_grpc: false
  dense_vector_name: "dense-text-vector"
  sparse_vector_name: "sparse-text-vector"
  use_sparse: true
  top_k: 8
```

Qdrant environment overrides: `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`.

For `Qdrant/bm25`, enable `IDF` on the sparse vector index in your Qdrant collection.

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

PDF notes:

- Each PDF page becomes one RAG chunk (`Slide 1`, `Slide 2`, ...).
- Ingestion extracts the page transcript with PyMuPDF, renders the page image, and asks the local Ollama model for a short slide description.
- The generated slide metadata is cached beside the PDF as `filename.pdf.slides.json`.
- Embeddings are built from the generated description plus the stored `TEXT_TRANSCRIPT`.
- If PDF vision enrichment fails for one PDF, that PDF is skipped and the rest of the ingest run continues.
- Oversized chunks are split into multiple embedding-safe chunks before sending them to Ollama. `EMBEDDING_MAX_CHARS` controls the target size, and `EMBEDDING_RETRIES` controls retries for failed embedding requests.
- Failed dense embedding chunks are listed in the logs and written to `rag/crawler/data/isis/meta/embedding_failures.json`.
- If a chunk still cannot fit because the metadata wrapper itself is too large, the fallback truncation is listed in the logs and written to `rag/crawler/data/isis/meta/embedding_truncations.json`, including both the original and truncated embedding text.
- If `fastembed` is not installed, ingest falls back to dense-only upsert and logs a warning instead of aborting after dense embeddings finish.

RAG probe (retrieval only, no LLM):

```bash
python3 scripts/rag_probe.py --config config.yaml
```

Useful options:

```bash
python3 scripts/rag_probe.py --config config.yaml --top-k 12
python3 scripts/rag_probe.py --config config.yaml --no-expand
python3 scripts/rag_probe.py --config config.yaml --json
python3 scripts/rag_probe.py --config config.yaml --full
python3 scripts/rag_probe.py --config config.yaml --show-expanded
```

Quality checks:

Inspect what ingestion would pack into chunks:

```bash
python3 scripts/inspect_ingest.py --config config.yaml --course-id 43321 --source-type file --limit 10
python3 scripts/inspect_ingest.py --config config.yaml --file-contains introprog-v04 --full
python3 scripts/inspect_ingest.py --config config.yaml --json
```

Trace the full RAG flow including retrieval, final user prompt, and LLM output:

```bash
python3 scripts/rag_trace.py --config config.yaml --question "Was ist ein AVL-Baum?"
python3 scripts/rag_trace.py --config config.yaml --question "Wie melde ich mich zur Klausur an?" --full-hits
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
