import logging
from pathlib import Path
from typing import Optional, Sequence, Union

import ollama  # type: ignore[import]

logger = logging.getLogger(__name__)

ImageInput = Union[str, bytes, Path]


class OllamaClient:
    """Lightweight async wrapper around the local Ollama server."""

    def __init__(self, model: str, system_prompt: str, host: Optional[str] = None):
        self.model_name = model
        self.system_prompt = system_prompt
        self.client = ollama.AsyncClient(host=host) if host else ollama.AsyncClient()

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


class OllamaVisionClient:
    """Synchronous multimodal wrapper for local Ollama inference."""

    def __init__(self, model: str, host: Optional[str] = None):
        self.model_name = model
        self.client = ollama.Client(host=host) if host else ollama.Client()

    def generate(self, user_message: str, images: Sequence[ImageInput]) -> str:
        if not images:
            raise ValueError("At least one image is required for multimodal generation.")

        response = self.client.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                    "images": list(images),
                }
            ],
            stream=False,
        )
        content = response.get("message", {}).get("content", "").strip()
        if not content:
            raise ValueError("Ollama returned an empty multimodal response.")
        logger.debug(
            "Received multimodal response from Ollama (%d chars) with model %s",
            len(content),
            self.model_name,
        )
        return content
