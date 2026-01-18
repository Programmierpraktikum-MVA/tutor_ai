# bot/handlers.py
import logging
from typing import Optional

from llm.ollama import OllamaClient

from rag.prompt import build_rag_user_message, format_sources
from rag.retrieve import QdrantRetriever

logger = logging.getLogger(__name__)


class Handlers:
    """Dispatches chat and command handling for Matrix messages (optional RAG)."""

    def __init__(self, llm_client: OllamaClient, retriever: Optional[QdrantRetriever] = None):
        self.llm = llm_client
        self.retriever = retriever

    async def handle_message(self, message: str, room_id: str, sender: str) -> str:
        logger.info("Handling chat message from %s in %s", sender, room_id)

        hits = []
        if self.retriever:
            hits = self.retriever.retrieve(message)

        user_prompt = build_rag_user_message(message, hits)
        answer = await self.llm.generate(user_prompt)

        sources_block = format_sources(hits)
        return f"{answer}\n\nQuellen:\n{sources_block}"

    async def handle_command(self, message: str, room_id: str, sender: str) -> Optional[str]:
        logger.info("Handling command from %s in %s: %s", sender, room_id, message)
        command, _, tail = message.lstrip("!").partition(" ")
        command = command.lower()

        if command in {"help", "h"}:
            return (
                "Verfügbare Befehle:\n"
                "!help - Diese Hilfe\n"
                "!status - Zeigt den Zustand des Bots"
            )

        if command == "status":
            rag_status = "an" if self.retriever else "aus"
            return f"TutorAI läuft. Modell: {self.llm.model_name} | RAG: {rag_status}"

        return f"Unbekannter Befehl '{command}'. Tippe !help für Hilfe."
