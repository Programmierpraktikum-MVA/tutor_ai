#!/usr/bin/env bash
set -euo pipefail

: "${ISIS_USERNAME:?Set ISIS_USERNAME for the crawler}"
: "${ISIS_PASSWORD:?Set ISIS_PASSWORD for the crawler}"

DATA_ROOT="${CRAWLER_DATA_DIR:-rag/crawler/data}"
CONFIG_PATH="${CONFIG_PATH:-config.yaml}"

python3 rag/crawler/selenium/main.py "$ISIS_USERNAME" "$ISIS_PASSWORD"
python3 -m rag.ingest --data-root "$DATA_ROOT" --config "$CONFIG_PATH"
