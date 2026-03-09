from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from qdrant_client.http.models import PointStruct

from db.qdrant import QdrantStore


class QdrantStoreTest(unittest.TestCase):
    @patch("db.qdrant.QdrantClient")
    def test_upsert_batches_points(self, client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        client_cls.return_value = mock_client
        store = QdrantStore(url="http://qdrant.local", api_key=None, collection_name="test")

        points = [
            PointStruct(id=str(index), vector={"dense": [0.1, 0.2]}, payload={"idx": index})
            for index in range(5)
        ]

        with patch.dict("os.environ", {"QDRANT_UPSERT_BATCH_SIZE": "2"}):
            store.upsert(points)

        self.assertEqual(mock_client.upsert.call_count, 3)
        first_call = mock_client.upsert.call_args_list[0]
        last_call = mock_client.upsert.call_args_list[-1]
        self.assertEqual(first_call.kwargs["collection_name"], "test")
        self.assertEqual(len(first_call.kwargs["points"]), 2)
        self.assertEqual(len(last_call.kwargs["points"]), 1)


if __name__ == "__main__":
    unittest.main()
