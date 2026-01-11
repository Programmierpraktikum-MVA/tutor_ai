
# Tutor AI

Tutor AI is an innovative project designed to harness the power of advanced language models to provide educational assistance. Built on locally hosted LLMs via Ollama, Tutor AI offers users personalized learning experiences and intelligent tutoring, including Q&A, brainstorming, and up-to-date information.

## Features (current)

- Matrix chatbot (no RAG): Matrix text → local Ollama (`gemma3:12b` by default) → reply back to the room
- Commands: `!help`, `!status`
- RAG ingestion pipeline (ISIS): parse → chunk → embed (Ollama) → upsert to Qdrant

## Prerequisites

- Python 3.8–3.11, pip, virtualenv
- Local Ollama with model `gemma3:12b` (or set your model in `config.yaml`)
- Matrix account + access token
- Qdrant instance reachable from this machine

## Setup (first time) 

1) Clone the repo and create/activate a virtual environment:
   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   ```
2) Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Für CPU-Only zusätzlich:
   ```bash
   pip install --index-url https://download.pytorch.org/whl/cpu \ 
   -r requirements-cpu.txt
   ```
   Für GPU-Server:
   ```bash
   pip install --index-url https://download.pytorch.org/whl/cu121 \ 
   -r requirements-cu121.txt
   ```
   

3) Copy `config.example.yaml` to `config.yaml` and fill in Matrix credentials, allowed room IDs; adjust Ollama host/model if needed.
4) Start Ollama once and pull the model:
   ```bash
   ollama serve
   ollama pull gemma3:12b
   ```

## Configuration (embeddings + Qdrant)

`config.yaml` supports:

```yaml
embeddings:
  model: "nomic-embed-text:v1.5"
  host: "http://localhost:11434"

qdrant:
  url: "http://localhost:6333"
  api_key: "REPLACE_ME"
  collection: "tutor_ai"
  prefer_grpc: false
```

You can also override Qdrant settings via environment variables:
`QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`.

## How to use

1) Start Ollama: `ollama serve`
2) Activate your virtual environment (if not already active):
   ```bash
   . .venv/bin/activate
   ```
3) From the repo root, start the bot:
   ```bash
   python3 -m bot.main
   ```
4) Invite the bot to a **non-E2E** room listed in `allowed_room_ids`. Any message in an allowed room triggers a reply; commands: `!help`, `!status`.

## RAG ingestion (ISIS data)

1) Ensure Ollama is running and the embedding model is available:
   ```bash
   ollama pull nomic-embed-text:v1.5
   ```
2) Fill in Qdrant settings in `config.yaml` (see `config.example.yaml` for keys).
3) Run the crawler to refresh `rag/crawler/data`:
   ```bash
   python3 rag/crawler/selenium/main.py <username> <password>
   ```
4) Ingest into Qdrant:
   ```bash
   python3 -m rag.ingest --data-root rag/crawler/data --config config.yaml
   ```

Optional flags:

```bash
python3 -m rag.ingest --course-id 43321
python3 -m rag.ingest --dry-run
```

To schedule regular updates, use a cron/systemd timer to run the crawler and ingestion script.
An example helper is provided at `scripts/run_crawl_and_ingest.sh` (expects `ISIS_USERNAME`,
`ISIS_PASSWORD`, and optional Qdrant env vars).

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Maximilian Hans - m.hans@tu-berlin.de

Project Link: [https://github.com/Programmierpraktikum-MVA/tutor_ai](https://github.com/Programmierpraktikum-MVA/tutor_ai)
