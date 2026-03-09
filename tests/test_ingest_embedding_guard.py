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

    def test_ingest_writes_truncation_report_with_original_and_truncated_text(self) -> None:
        chunks = [
            ingest.ParsedChunk(
                text="tiny body",
                source_type="course_info",
                context_section="Section " + ("X" * 400),
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
            with patch.dict("os.environ", {"EMBEDDING_MAX_CHARS": "300"}):
                with patch.object(ingest, "build_chunks", return_value=chunks):
                    with patch.object(ingest, "OllamaEmbeddingClient", return_value=fake_embed_client):
                        with patch.object(ingest, "QdrantStore", return_value=fake_store):
                            ingest.ingest(Path(tmpdir), _fake_config(use_sparse=False), course_id=None, dry_run=False)

            report_path = Path(tmpdir) / "isis" / "meta" / "embedding_truncations.json"
            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(report), 1)
            self.assertEqual(report[0]["file_origin"], "a.json")
            self.assertGreater(report[0]["original_embedding_chars"], report[0]["truncated_embedding_chars"])
            self.assertIn("search_document:", report[0]["original_embedding_text"])
            self.assertLessEqual(len(report[0]["truncated_embedding_text"]), 300)

    def test_ingest_splits_oversized_chunk_into_multiple_embedding_chunks(self) -> None:
        chunks = [
            ingest.ParsedChunk(
                text="very long chunk " * 300,
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
            with patch.dict("os.environ", {"EMBEDDING_MAX_CHARS": "400"}):
                with patch.object(ingest, "build_chunks", return_value=chunks):
                    with patch.object(ingest, "OllamaEmbeddingClient", return_value=fake_embed_client):
                        with patch.object(ingest, "QdrantStore", return_value=fake_store):
                            ingest.ingest(Path(tmpdir), _fake_config(use_sparse=False), course_id=None, dry_run=False)

            truncation_report = Path(tmpdir) / "isis" / "meta" / "embedding_truncations.json"
            self.assertFalse(truncation_report.exists())

        self.assertEqual(len(fake_store.upsert_calls), 1)
        points = fake_store.upsert_calls[0]
        self.assertGreater(len(points), 1)
        for point in points:
            self.assertEqual(point.payload["file_origin"], "a.json")
            self.assertIn("chunk_part_count", point.payload)
        for text in fake_embed_client.calls:
            self.assertLessEqual(len(text), 400)

    def test_split_chunk_for_embedding_keeps_single_normalized_pdf_part(self) -> None:
        chunk = ingest.ParsedChunk(
            text="Main topic: Topic\nShort description: Desc\nTEXT_TRANSCRIPT:\nAlpha          Beta          Gamma",
            source_type="file",
            context_section="File: slides.pdf",
            context_activity="Slide 1",
            url="https://example.com/slides",
            file_origin="slides.pdf",
            course_id="43321",
            chunk_index=0,
            page_number=1,
            page_count=1,
            vision_description="Main topic: Topic\nShort description: Desc",
            text_transcript="Alpha          Beta          Gamma",
        )

        with patch.dict("os.environ", {"EMBEDDING_TARGET_CHARS": "180", "EMBEDDING_MAX_CHARS": "220"}):
            parts = ingest._split_chunk_for_embedding(chunk, 220)

        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].text_transcript, "Alpha Beta Gamma")
        self.assertIn("Alpha Beta Gamma", parts[0].text)
        self.assertLessEqual(len(ingest._format_embedding_text(parts[0])), 180)

    def test_split_chunk_for_embedding_uses_conservative_target_below_hard_cap(self) -> None:
        chunk = ingest.ParsedChunk(
            text="dense text " * 160,
            source_type="activity",
            context_section="Section A",
            context_activity="forum",
            url="https://example.com/forum",
            file_origin="activities.json",
            course_id="43321",
            chunk_index=11,
        )

        with patch.dict("os.environ", {}, clear=False):
            parts = ingest._split_chunk_for_embedding(chunk, 1800)

        self.assertGreater(len(parts), 1)
        for part in parts:
            self.assertLessEqual(len(ingest._format_embedding_text(part)), ingest.DEFAULT_EMBEDDING_TARGET_CHARS)


if __name__ == "__main__":
    unittest.main()
