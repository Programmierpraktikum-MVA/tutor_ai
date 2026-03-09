from __future__ import annotations

import unittest

from rag.prompt import build_rag_context, build_rag_user_message
from rag.retrieve import RetrievalHit


class RagPromptTest(unittest.TestCase):
    def test_build_rag_context_formats_hits(self) -> None:
        hits = [
            RetrievalHit(
                score=0.9,
                text="AVL trees keep balance information.",
                url="https://example.com",
                file_origin="slides.pdf",
                course_id="43321",
                source_type="file",
                context_section="File: slides.pdf",
                context_activity="Slide 3",
                chunk_index=2,
            )
        ]

        context = build_rag_context("What is an AVL tree?", hits)

        self.assertIn("[1] AVL trees keep balance information.", context)
        self.assertIn("file=slides.pdf", context)
        self.assertIn("activity=Slide 3", context)

    def test_build_rag_user_message_uses_shared_context_builder(self) -> None:
        hits = [
            RetrievalHit(
                score=0.7,
                text="Arrays use fixed-size contiguous memory.",
                url="https://example.com/arrays",
                file_origin="arrays.pdf",
                course_id="43321",
                source_type="file",
                context_section="File: arrays.pdf",
                context_activity="Slide 5",
                chunk_index=4,
            )
        ]

        message = build_rag_user_message("What is an array?", hits)

        self.assertIn("Frage: What is an array?", message)
        self.assertIn("KONTEXT:", message)
        self.assertIn("Arrays use fixed-size contiguous memory.", message)
        self.assertIn("file=arrays.pdf", message)


if __name__ == "__main__":
    unittest.main()
