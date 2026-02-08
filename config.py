from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Set

import yaml


DEFAULT_SYSTEM_PROMPT = (
    "Du bist TutorAI, ein hilfreicher deutschsprachiger Studienassistent. "
    "Antworte knapp, präzise und freundlich. "
    "Falls dir Informationen fehlen, sei ehrlich und mache klare Vorschläge, "
    "wie der Nutzer weiter vorgehen kann."
)

DEFAULT_ALLOWED_ROOMS = {"!JSFGmEgwCdNkLZEhuY:matrix.org"}


@dataclass
class MatrixConfig:
    homeserver_url: str
    user_id: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_endpoint: Optional[str] = None
    client_id: Optional[str] = None
    token_expires_at: Optional[int] = None
    device_id: str = "BOTDEVICE"
    store_path: str = "./store"


@dataclass
class OllamaConfig:
    model: str = "llama3.1"
    host: Optional[str] = None
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


@dataclass
class EmbeddingsConfig:
    model: str = "nomic-embed-text:v1.5"
    host: Optional[str] = None
    sparse_model: str = "Qdrant/bm25"


@dataclass
class QdrantConfig:
    url: str
    api_key: Optional[str] = None
    collection: str = "tutor_ai"
    prefer_grpc: bool = False
    dense_vector_name: str = "dense-text-vector"
    sparse_vector_name: str = "sparse-text-vector"
    use_sparse: bool = True
    top_k: int = 8


class Config:
    """Thin YAML-backed configuration used by the Matrix bot and LLM layer."""

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.matrix = self._load_matrix(raw.get("matrix", {}))
        self.ollama = self._load_ollama(raw.get("ollama", {}), raw.get("prompts", {}))
        self.embeddings = self._load_embeddings(raw.get("embeddings", {}), raw.get("ollama", {}))
        self.qdrant = self._load_qdrant(raw.get("qdrant", {}))
        self.allowed_rooms = self._load_allowed_rooms(raw)

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        config_path = Path(path)
        with config_path.open("r") as f:
            raw = yaml.safe_load(f) or {}
        return cls(raw)

    def _load_matrix(self, data: Dict[str, Any]) -> MatrixConfig:
        homeserver_url = data.get("homeserver_url")
        user_id = data.get("user_id")
        if not homeserver_url or not user_id:
            missing = "homeserver_url" if not homeserver_url else "user_id"
            raise ValueError(f"Missing required matrix config key: {missing}")

        return MatrixConfig(
            homeserver_url=homeserver_url,
            user_id=user_id,
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_endpoint=data.get("token_endpoint"),
            client_id=data.get("client_id"),
            token_expires_at=data.get("token_expires_at"),
            device_id=data.get("device_id", "BOTDEVICE"),
            store_path=data.get("store_path", "./store"),
        )

    def _load_ollama(self, data: Dict[str, Any], prompts: Dict[str, Any]) -> OllamaConfig:
        system_prompt = prompts.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
        return OllamaConfig(
            model=data.get("model", "llama3.1"),
            host=data.get("host"),
            system_prompt=system_prompt,
        )

    def _load_embeddings(self, data: Dict[str, Any], ollama_data: Dict[str, Any]) -> EmbeddingsConfig:
        return EmbeddingsConfig(
            model=data.get("model", "nomic-embed-text:v1.5"),
            host=data.get("host", ollama_data.get("host")),
            sparse_model=data.get("sparse_model", "Qdrant/bm25"),
        )

    def _load_qdrant(self, data: Dict[str, Any]) -> Optional[QdrantConfig]:
        url = data.get("url")
        if not url:
            return None
        return QdrantConfig(
            url=url,
            api_key=data.get("api_key"),
            collection=data.get("collection", "tutor_ai"),
            prefer_grpc=bool(data.get("prefer_grpc", False)),
            dense_vector_name=data.get("dense_vector_name", "dense-text-vector"),
            sparse_vector_name=data.get("sparse_vector_name", "sparse-text-vector"),
            use_sparse=bool(data.get("use_sparse", True)),
            top_k=int(data.get("top_k", 8)),
        )

    def _load_allowed_rooms(self, raw: Dict[str, Any]) -> Set[str]:
        # Support both spellings in case of typos in existing files.
        value = raw.get("allowed_room_ids")
        if value is None:
            value = raw.get("allowed_rooms_ids")

        if value is None:
            return set(DEFAULT_ALLOWED_ROOMS)

        if isinstance(value, str):
            rooms = {room.strip() for room in value.split(",") if room.strip()}
        elif isinstance(value, list):
            rooms = {str(room).strip() for room in value if str(room).strip()}
        else:
            raise ValueError("allowed_room_ids must be a string or list")

        return rooms or set(DEFAULT_ALLOWED_ROOMS)
