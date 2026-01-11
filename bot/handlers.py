import logging
from typing import Optional

from llm.ollama import OllamaClient

logger = logging.getLogger(__name__)


class Handlers:
    """Dispatches chat and command handling for Matrix messages."""

    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    async def handle_message(self, message: str, room_id: str, sender: str) -> str:
        logger.info("Handling chat message from %s in %s", sender, room_id)
        return await self.llm.generate(message)

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
            return f"TutorAI läuft. Modell: {self.llm.model_name}"

        return f"Unbekannter Befehl '{command}'. Tippe !help für Hilfe."
