from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import fitz  # type: ignore[import]

import rag.ingest as ingest


def _fake_config(model: str = "gemma3:12b", host: str = "http://localhost:11434") -> SimpleNamespace:
    return SimpleNamespace(ollama=SimpleNamespace(model=model, host=host))


def _create_pdf(path: Path, page_texts: list[str]) -> None:
    doc = fitz.open()
    try:
        for page_text in page_texts:
            page = doc.new_page()
            page.insert_text((72, 72), page_text)
        doc.save(path)
    finally:
        doc.close()


class _FakeVisionClient:
    calls: list[str] = []
    responses: list[str] = []

    def __init__(self, model: str, host: str | None = None) -> None:
        self.model = model
        self.host = host

    def generate(self, user_message: str, images: list[bytes]) -> str:
        self.__class__.calls.append(user_message)
        if not images:
            raise AssertionError("expected slide image bytes")
        return self.__class__.responses[len(self.__class__.calls) - 1]


class PdfSlideEnrichmentTest(unittest.TestCase):
    def setUp(self) -> None:
        _FakeVisionClient.calls = []
        _FakeVisionClient.responses = [
            "Main topic: Intro\nShort description: Course overview.",
            "Main topic: Arrays\nShort description: Introduces array basics.",
        ]

    def test_pdf_parsing_creates_one_chunk_per_slide_and_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "slides.pdf"
            _create_pdf(pdf_path, ["Hello Slide 1", "Hello Slide 2"])

            with patch.object(ingest, "OllamaVisionClient", _FakeVisionClient):
                chunks = ingest.parse_downloaded_file(
                    pdf_path,
                    "43321",
                    "isis/files/43321/slides.pdf",
                    config=_fake_config(),
                )

            self.assertEqual(len(chunks), 2)
            self.assertEqual([chunk.context_activity for chunk in chunks], ["Slide 1", "Slide 2"])
            self.assertEqual(chunks[0].page_number, 1)
            self.assertEqual(chunks[0].page_count, 2)
            self.assertEqual(chunks[0].text_transcript.strip(), "Hello Slide 1")
            self.assertEqual(
                chunks[0].vision_description,
                "Main topic: Intro\nShort description: Course overview.",
            )
            self.assertIn("TEXT_TRANSCRIPT:\nHello Slide 1", chunks[0].text)
            self.assertEqual(len(_FakeVisionClient.calls), 2)
            self.assertIn("TEXT_TRANSCRIPT:\nHello Slide 1", _FakeVisionClient.calls[0])

            payload = ingest._payload_from_chunk(chunks[0])
            self.assertEqual(payload["page_number"], 1)
            self.assertEqual(payload["page_count"], 2)
            self.assertEqual(payload["text_transcript"], "Hello Slide 1")
            self.assertIn("Main topic: Intro", str(payload["vision_description"]))

            sidecar_path = pdf_path.with_name("slides.pdf.slides.json")
            self.assertTrue(sidecar_path.exists())
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual(sidecar["header"]["model_name"], "gemma3:12b")
            self.assertEqual(len(sidecar["slides"]), 2)

            _FakeVisionClient.calls = []
            _FakeVisionClient.responses = []
            with patch.object(ingest, "OllamaVisionClient", _FakeVisionClient):
                cached_chunks = ingest.parse_downloaded_file(
                    pdf_path,
                    "43321",
                    "isis/files/43321/slides.pdf",
                    config=_fake_config(),
                )
            self.assertEqual(len(cached_chunks), 2)
            self.assertEqual(_FakeVisionClient.calls, [])

    def test_pdf_cache_invalidates_on_model_change_prompt_version_and_pdf_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "slides.pdf"
            _create_pdf(pdf_path, ["Slide A"])

            with patch.object(ingest, "OllamaVisionClient", _FakeVisionClient):
                ingest.parse_downloaded_file(pdf_path, "43321", "slides.pdf", config=_fake_config("model-a"))
            self.assertEqual(len(_FakeVisionClient.calls), 1)

            _FakeVisionClient.calls = []
            _FakeVisionClient.responses = ["Main topic: Regenerated\nShort description: New model."]
            with patch.object(ingest, "OllamaVisionClient", _FakeVisionClient):
                ingest.parse_downloaded_file(pdf_path, "43321", "slides.pdf", config=_fake_config("model-b"))
            self.assertEqual(len(_FakeVisionClient.calls), 1)

            _FakeVisionClient.calls = []
            _FakeVisionClient.responses = ["Main topic: Prompt\nShort description: Prompt version."]
            with patch.object(ingest, "OllamaVisionClient", _FakeVisionClient):
                with patch.object(ingest, "PDF_SLIDE_VISION_PROMPT_VERSION", "v2"):
                    ingest.parse_downloaded_file(pdf_path, "43321", "slides.pdf", config=_fake_config("model-b"))
            self.assertEqual(len(_FakeVisionClient.calls), 1)

            _create_pdf(pdf_path, ["Slide B changed"])
            _FakeVisionClient.calls = []
            _FakeVisionClient.responses = ["Main topic: Hash\nShort description: Pdf changed."]
            with patch.object(ingest, "OllamaVisionClient", _FakeVisionClient):
                ingest.parse_downloaded_file(pdf_path, "43321", "slides.pdf", config=_fake_config("model-b"))
            self.assertEqual(len(_FakeVisionClient.calls), 1)

    def test_non_pdf_files_keep_existing_chunking(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            text_path = Path(tmpdir) / "notes.txt"
            text_path.write_text("alpha beta gamma", encoding="utf-8")

            chunks = ingest.parse_downloaded_file(text_path, "43321", "notes.txt")

            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].context_activity, "Downloaded file")
            self.assertIsNone(chunks[0].page_number)
            self.assertIsNone(chunks[0].vision_description)
            self.assertEqual(chunks[0].text, "alpha beta gamma")

    def test_build_chunks_skips_failed_pdf_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir)
            files_dir = data_root / "isis" / "files" / "43321" / "week1"
            files_dir.mkdir(parents=True)
            pdf_path = files_dir / "slides.pdf"
            txt_path = files_dir / "notes.txt"
            _create_pdf(pdf_path, ["Broken slide"])
            txt_path.write_text("still ingest this", encoding="utf-8")

            with patch.object(ingest, "_resolve_pdf_slide_cache", side_effect=RuntimeError("vision failed")):
                chunks = ingest.build_chunks(data_root, "43321", config=_fake_config())

            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].text, "still ingest this")
            self.assertEqual(chunks[0].file_origin, "isis/files/43321/week1/notes.txt")


if __name__ == "__main__":
    unittest.main()
