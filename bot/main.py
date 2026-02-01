import asyncio
import os
import sys
from pathlib import Path

import logging

# Ensure project root is on sys.path when running via `python bot/main.py`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from log_config import setup_logging
from bot.handlers import Handlers
from bot.matrix_io import MatrixBot
from bot.router import Router
from llm.ollama import OllamaClient
from rag.retrieve import QdrantRetriever


async def main() -> None:
    setup_logging()

    config_path = os.environ.get("CONFIG_PATH", "config.yaml")
    cfg = Config.load(config_path)

    logging.getLogger(__name__).info(
        "Starting TutorAI Matrix bot for user %s on %s using model %s",
        cfg.matrix.user_id,
        cfg.matrix.homeserver_url,
        cfg.ollama.model,
    )

    llm_client = OllamaClient(
        model=cfg.ollama.model,
        system_prompt=cfg.ollama.system_prompt,
        host=cfg.ollama.host,
    )

    # Optional RAG: only enabled when qdrant config is present.
    retriever = None
    if cfg.qdrant:
        retriever = QdrantRetriever(
            qdrant_cfg=cfg.qdrant,
            embeddings_cfg=cfg.embeddings,
            top_k=5,
        )

    handlers = Handlers(llm_client, retriever=retriever)
    router = Router(handlers)
    bot = MatrixBot(
        cfg.matrix,
        router.route,
        allowed_rooms=cfg.allowed_rooms,
        config_path=config_path,
    )

    try:
        await bot.start()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutting down bot...")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
