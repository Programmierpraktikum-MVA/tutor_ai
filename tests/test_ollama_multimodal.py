from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from llm.ollama import OllamaVisionClient


class OllamaVisionClientTest(unittest.TestCase):
    @patch("llm.ollama.ollama.Client")
    def test_generate_sends_multimodal_message(self, client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {
                "content": "Main topic: Sorting\nShort description: Slide about quicksort.",
            }
        }
        client_cls.return_value = mock_client

        client = OllamaVisionClient(model="gemma3:12b", host="http://localhost:11434")
        result = client.generate("prompt text", [b"png-bytes"])

        self.assertEqual(
            result,
            "Main topic: Sorting\nShort description: Slide about quicksort.",
        )
        mock_client.chat.assert_called_once_with(
            model="gemma3:12b",
            messages=[
                {
                    "role": "user",
                    "content": "prompt text",
                    "images": [b"png-bytes"],
                }
            ],
            stream=False,
        )


if __name__ == "__main__":
    unittest.main()
