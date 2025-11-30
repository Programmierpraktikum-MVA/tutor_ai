from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


DEFAULT_SYSTEM_PROMPT = (
    "Du bist TutorAI, ein hilfreicher deutschsprachiger Studienassistent. "
    "Antworte knapp, präzise und freundlich. "
    "Falls dir Informationen fehlen, sei ehrlich und mache klare Vorschläge, "
    "wie der Nutzer weiter vorgehen kann."
)


@dataclass
class MatrixConfig:
    homeserver_url: str
    user_id: str
    access_token: str
    device_id: str = "BOTDEVICE"
    store_path: str = "./store"


@dataclass
class OllamaConfig:
    model: str = "llama3.1"
    host: Optional[str] = None
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class Config:
    """Thin YAML-backed configuration used by the Matrix bot and LLM layer."""

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.matrix = self._load_matrix(raw.get("matrix", {}))
        self.ollama = self._load_ollama(raw.get("ollama", {}), raw.get("prompts", {}))

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        config_path = Path(path)
        with config_path.open("r") as f:
            raw = yaml.safe_load(f) or {}
        return cls(raw)

    def _load_matrix(self, data: Dict[str, Any]) -> MatrixConfig:
        try:
            return MatrixConfig(
                homeserver_url=data["homeserver_url"],
                user_id=data["user_id"],
                access_token=data["access_token"],
                device_id=data.get("device_id", "BOTDEVICE"),
                store_path=data.get("store_path", "./store"),
            )
        except KeyError as exc:
            raise ValueError(f"Missing required matrix config key: {exc.args[0]}") from exc

    def _load_ollama(self, data: Dict[str, Any], prompts: Dict[str, Any]) -> OllamaConfig:
        system_prompt = prompts.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
        return OllamaConfig(
            model=data.get("model", "llama3.1"),
            host=data.get("host"),
            system_prompt=system_prompt,
        )
