import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from qdrant_client.models import Distance, VectorParams, PointStruct
from shared.qdrant.client import QdrantManager


@pytest.mark.unit
class TestQdrantManager:
    @patch('shared.qdrant.client.QdrantClient')
    def test_init(self, mock_qdrant_client):
        manager = QdrantManager()
        assert manager.client is not None
        
    def test_get_collection_name(self):
        manager = QdrantManager.__new__(QdrantManager)
        chat_type_id = uuid4()
        collection_name = manager.get_collection_name(chat_type_id)
        assert collection_name == f"chat_type_{chat_type_id}"
        
    @patch('shared.qdrant.client.QdrantClient')
    def test_create_collection_new(self, mock_qdrant_client):
        mock_client = MagicMock()
        mock_client.get_collections.return_value.collections = []
        mock_qdrant_client.return_value = mock_client
        
        manager = QdrantManager()
        chat_type_id = uuid4()
        
        result = manager.create_collection(chat_type_id, vector_size=384)
        
        assert result is True
        mock_client.create_collection.assert_called_once()
        
    @patch('shared.qdrant.client.QdrantClient')
    def test_create_collection_exists(self, mock_qdrant_client):
        chat_type_id = uuid4()
        collection_name = f"chat_type_{chat_type_id}"
        
        mock_collection = MagicMock()
        mock_collection.name = collection_name
        
        mock_client = MagicMock()
        mock_client.get_collections.return_value.collections = [mock_collection]
        mock_qdrant_client.return_value = mock_client
        
        manager = QdrantManager()
        result = manager.create_collection(chat_type_id)
        
        assert result is True
        mock_client.create_collection.assert_not_called()
        
    @patch('shared.qdrant.client.QdrantClient')
    def test_delete_collection(self, mock_qdrant_client):
        mock_client = MagicMock()
        mock_qdrant_client.return_value = mock_client
        
        manager = QdrantManager()
        chat_type_id = uuid4()
        
        result = manager.delete_collection(chat_type_id)
        
        assert result is True
        mock_client.delete_collection.assert_called_once()
        
    @patch('shared.qdrant.client.QdrantClient')
    def test_insert_chunks(self, mock_qdrant_client):
        mock_client = MagicMock()
        mock_qdrant_client.return_value = mock_client
        
        manager = QdrantManager()
        chat_type_id = uuid4()
        
        chunks = [
            {"question": "Q1", "answer": "A1", "metadata": {}},
            {"question": "Q2", "answer": "A2", "metadata": {}}
        ]
        embeddings = [[0.1] * 384, [0.2] * 384]
        
        point_ids = manager.insert_chunks(chat_type_id, chunks, embeddings)
        
        assert len(point_ids) == 2
        mock_client.upsert.assert_called_once()
        
    @patch('shared.qdrant.client.QdrantClient')
    def test_insert_chunks_mismatch(self, mock_qdrant_client):
        mock_client = MagicMock()
        mock_qdrant_client.return_value = mock_client
        
        manager = QdrantManager()
        chat_type_id = uuid4()
        
        chunks = [{"question": "Q1", "answer": "A1", "metadata": {}}]
        embeddings = [[0.1] * 384, [0.2] * 384]
        
        with pytest.raises(ValueError, match="must match"):
            manager.insert_chunks(chat_type_id, chunks, embeddings)
            
    @patch('shared.qdrant.client.QdrantClient')
    def test_search(self, mock_qdrant_client):
        mock_point = MagicMock()
        mock_point.id = "point_1"
        mock_point.score = 0.95
        mock_point.payload = {
            "question": "Test question",
            "answer": "Test answer",
            "metadata": {"source": "test"}
        }
        
        mock_client = MagicMock()
        mock_client.query_points.return_value.points = [mock_point]
        mock_qdrant_client.return_value = mock_client
        
        manager = QdrantManager()
        chat_type_id = uuid4()
        query_embedding = [0.1] * 384
        
        results = manager.search(chat_type_id, query_embedding, limit=5)
        
        assert len(results) == 1
        assert results[0]["id"] == "point_1"
        assert results[0]["score"] == 0.95
        assert results[0]["question"] == "Test question"
        
    @patch('shared.qdrant.client.QdrantClient')
    def test_get_collection_info(self, mock_qdrant_client):
        mock_collection_info = MagicMock()
        mock_collection_info.vectors_count = 100
        mock_collection_info.points_count = 100
        mock_collection_info.status = "green"
        
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection_info
        mock_qdrant_client.return_value = mock_client
        
        manager = QdrantManager()
        chat_type_id = uuid4()
        
        info = manager.get_collection_info(chat_type_id)
        
        assert info is not None
        assert info["vectors_count"] == 100
        assert info["points_count"] == 100
        assert info["status"] == "green"
        
    @patch('shared.qdrant.client.QdrantClient')
    def test_get_collection_info_not_found(self, mock_qdrant_client):
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("Not found")
        mock_qdrant_client.return_value = mock_client
        
        manager = QdrantManager()
        chat_type_id = uuid4()
        
        info = manager.get_collection_info(chat_type_id)
        
        assert info is None
