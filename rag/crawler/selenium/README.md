# Tutor AI Scraper (Selenium)

Scrapers for ISIS and MOSES. Code lives in `rag/crawler/selenium`, outputs are written to `rag/crawler/data`.

## Prerequisites

- Python 3.8+
- pip and venv/virtualenv
- ffmpeg (for audio extraction)

## Setup

1) Create a virtualenv (Python 3):

```bash
python3 -m venv SelEnv
```

2) Activate it and install deps (CPU):

```bash
pip install -r requirements.txt
```

For CUDA builds of PyTorch:

```bash
pip install -r requirements-cuda.txt
```

3) Install ffmpeg:

```bash
sudo apt install ffmpeg
```

## Usage

Run from repo root:

```bash
python3 rag/crawler/selenium/main.py <username> <password>
```

Optional environment variables:

- `CRAWLER_DATA_DIR` (default: `rag/crawler/data`)
- `ISIS_COURSE_ID` to scrape a single course (e.g. `43321` or comma-separated list)
- `WHISPER_DEVICE` (`cpu` or `cuda`)

Output data is written to `rag/crawler/data` by default (override with `CRAWLER_DATA_DIR`).

To clear all crawler output data:

```bash
rm -rf rag/crawler/data/*
```

If you set `CRAWLER_DATA_DIR`, clear that directory instead:

```bash
rm -rf "${CRAWLER_DATA_DIR:?}"/*
```

## Layout

```text
rag/crawler/selenium/
├── main.py
├── scraper.py
├── scraperMoses.py
├── transcribe.py
├── config.json
├── IsisModules/
├── IsisForums/
├── IsisPDFs/
├── IsisCourseIdManager/
├── MosesModules/
└── misc/

rag/crawler/data/
├── isis/
│   ├── course_infos/
│   ├── forums/
│   ├── pdfs/
│   ├── videos/
│   └── meta/
└── moses/
    ├── course_infos/
    └── meta/
```
