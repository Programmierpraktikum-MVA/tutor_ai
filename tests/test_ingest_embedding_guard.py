from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json

import rag.ingest as ingest


def _fake_config(use_sparse: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        embeddings=SimpleNamespace(
            model="nomic-embed-text:v1.5",
            host="http://localhost:11434",
            sparse_model="Qdrant/bm25",
        ),
        qdrant=SimpleNamespace(
            url="http://qdrant.local",
            api_key=None,
            collection="test_collection",
            dense_vector_name="dense-text-vector",
            sparse_vector_name="sparse-text-vector",
            use_sparse=use_sparse,
            prefer_grpc=False,
        ),
    )


class _FakeEmbedClient:
    def __init__(self, model: str, host: str | None = None) -> None:
        self.model = model
        self.host = host
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        if "bad embedding input" in text:
            raise RuntimeError("runner crashed")
        return [0.1, 0.2, 0.3]


class _FakeStore:
    def __init__(self, *args, **kwargs) -> None:
        self.ensure_calls = []
        self.upsert_calls = []

    def ensure_collection(self, *args, **kwargs) -> None:
        self.ensure_calls.append((args, kwargs))

    def upsert(self, points) -> None:
        self.upsert_calls.append(points)


class IngestEmbeddingGuardTest(unittest.TestCase):
    def test_truncate_embedding_input_keeps_prefix_and_limit(self) -> None:
        text = "search_document: " + ("alpha " * 600)

        truncated, was_truncated = ingest._truncate_embedding_input(text, 1800)

        self.assertTrue(was_truncated)
        self.assertTrue(truncated.startswith("search_document: "))
        self.assertLessEqual(len(truncated), 1800)

    def test_ingest_skips_failed_embedding_chunk_and_upserts_rest(self) -> None:
        chunks = [
            ingest.ParsedChunk(
                text="good chunk",
                source_type="course_info",
                context_section="Section A",
                context_activity="Overview",
                url="https://example.com/a",
                file_origin="a.json",
                course_id="43321",
                chunk_index=0,
            ),
            ingest.ParsedChunk(
                text="bad embedding input",
                source_type="course_info",
                context_section="Section B",
                context_activity="Overview",
                url="https://example.com/b",
                file_origin="b.json",
                course_id="43321",
                chunk_index=1,
            ),
        ]

        fake_store = _FakeStore()
        fake_embed_client = _FakeEmbedClient(model="nomic-embed-text:v1.5")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ingest, "build_chunks", return_value=chunks):
                with patch.object(ingest, "OllamaEmbeddingClient", return_value=fake_embed_client):
                    with patch.object(ingest, "QdrantStore", return_value=fake_store):
                        ingest.ingest(Path(tmpdir), _fake_config(use_sparse=False), course_id=None, dry_run=False)

            report_path = Path(tmpdir) / "isis" / "meta" / "embedding_failures.json"
            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(report), 1)
            self.assertEqual(report[0]["file_origin"], "b.json")
            self.assertIn("runner crashed", report[0]["error"])

        self.assertEqual(len(fake_store.upsert_calls), 1)
        points = fake_store.upsert_calls[0]
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].payload["file_origin"], "a.json")

    def test_ingest_falls_back_to_dense_only_when_sparse_embeddings_unavailable(self) -> None:
        chunks = [
            ingest.ParsedChunk(
                text="good chunk",
                source_type="course_info",
                context_section="Section A",
                context_activity="Overview",
                url="https://example.com/a",
                file_origin="a.json",
                course_id="43321",
                chunk_index=0,
            )
        ]

        fake_store = _FakeStore()
        fake_embed_client = _FakeEmbedClient(model="nomic-embed-text:v1.5")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ingest, "build_chunks", return_value=chunks):
                with patch.object(ingest, "OllamaEmbeddingClient", return_value=fake_embed_client):
                    with patch.object(ingest, "QdrantStore", return_value=fake_store):
                        with patch.object(
                            ingest,
                            "_build_sparse_embeddings",
                            side_effect=RuntimeError("fastembed is required for sparse embeddings."),
                        ):
                            ingest.ingest(Path(tmpdir), _fake_config(use_sparse=True), course_id=None, dry_run=False)

        self.assertEqual(len(fake_store.upsert_calls), 1)
        points = fake_store.upsert_calls[0]
        self.assertEqual(len(points), 1)
        vector_payload = points[0].vector
        self.assertIn("dense-text-vector", vector_payload)
        self.assertNotIn("sparse-text-vector", vector_payload)


if __name__ == "__main__":
    unittest.main()
