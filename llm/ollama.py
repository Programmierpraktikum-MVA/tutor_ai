import logging
from typing import Optional

from ollama import AsyncClient  # type: ignore[import]

logger = logging.getLogger(__name__)


class OllamaClient:
    """Lightweight async wrapper around the local Ollama server."""

    def __init__(self, model: str, system_prompt: str, host: Optional[str] = None):
        self.model_name = model
        self.system_prompt = system_prompt
        self.client = AsyncClient(host=host) if host else AsyncClient()

    async def generate(self, user_message: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        response_chunks: list[str] = []

        logger.debug("Sending prompt to Ollama with model %s", self.model_name)
        async for part in await self.client.chat(
            model=self.model_name, messages=messages, stream=True
        ):
            chunk = part.get("message", {}).get("content", "")
            if chunk:
                response_chunks.append(chunk)

        full_response = "".join(response_chunks).strip()
        logger.debug("Received response from Ollama (%d chars)", len(full_response))
        return full_response or "Ich konnte leider keine Antwort generieren."
