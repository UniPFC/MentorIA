import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from src.rag.engine.retriever import KnowledgeRetriever


@pytest.mark.unit
class TestKnowledgeRetriever:
    @pytest.fixture
    def mock_qdrant_manager(self):
        manager = MagicMock()
        manager.search.return_value = [
            {
                "id": "chunk_1",
                "score": 0.95,
                "question": "What is AI?",
                "answer": "AI is artificial intelligence",
                "metadata": {"source": "doc1.txt"}
            },
            {
                "id": "chunk_2",
                "score": 0.85,
                "question": "What is ML?",
                "answer": "ML is machine learning",
                "metadata": {"source": "doc2.txt"}
            }
        ]
        return manager
        
    @pytest.fixture
    def mock_embedding_engine(self):
        engine = MagicMock()
        engine.embed_single.return_value = [0.1] * 384
        return engine
        
    def test_search_chunks(self, mock_qdrant_manager, mock_embedding_engine):
        retriever = KnowledgeRetriever(
            qdrant_manager=mock_qdrant_manager,
            embedding_engine=mock_embedding_engine
        )
        
        chat_type_id = uuid4()
        query = "What is AI?"
        
        chunks = retriever.search(
            chat_type_id=chat_type_id,
            query=query,
            limit=5
        )
        
        assert len(chunks) == 2
        assert chunks[0]["score"] == 0.95
        assert chunks[0]["question"] == "What is AI?"
        mock_embedding_engine.embed_single.assert_called_once_with(query)
        mock_qdrant_manager.search.assert_called_once()
        
    def test_search_with_score_threshold(self, mock_qdrant_manager, mock_embedding_engine):
        retriever = KnowledgeRetriever(
            qdrant_manager=mock_qdrant_manager,
            embedding_engine=mock_embedding_engine
        )
        
        chat_type_id = uuid4()
        query = "What is AI?"
        
        chunks = retriever.search(
            chat_type_id=chat_type_id,
            query=query,
            limit=5,
            score_threshold=0.9
        )
        
        mock_qdrant_manager.search.assert_called_once()
        call_args = mock_qdrant_manager.search.call_args
        assert call_args[1]["score_threshold"] == 0.9
        
    def test_search_empty_results(self, mock_qdrant_manager, mock_embedding_engine):
        mock_qdrant_manager.search.return_value = []
        
        retriever = KnowledgeRetriever(
            qdrant_manager=mock_qdrant_manager,
            embedding_engine=mock_embedding_engine
        )
        
        chat_type_id = uuid4()
        chunks = retriever.search(chat_type_id, "query", limit=5)
        
        assert len(chunks) == 0
    
    def test_search_error_handling(self, mock_qdrant_manager, mock_embedding_engine):
        mock_qdrant_manager.search.side_effect = Exception("Search error")
        
        retriever = KnowledgeRetriever(
            qdrant_manager=mock_qdrant_manager,
            embedding_engine=mock_embedding_engine
        )
        
        chat_type_id = uuid4()
        
        with pytest.raises(Exception, match="Search error"):
            retriever.search(chat_type_id, "query", limit=5)
    
    def test_search_many_deduplication(self, mock_qdrant_manager, mock_embedding_engine):
        mock_qdrant_manager.search.side_effect = [
            [
                {"id": "chunk_1", "score": 0.95, "question": "Q1", "answer": "A1"},
                {"id": "chunk_2", "score": 0.85, "question": "Q2", "answer": "A2"}
            ],
            [
                {"id": "chunk_2", "score": 0.90, "question": "Q2", "answer": "A2"},
                {"id": "chunk_3", "score": 0.80, "question": "Q3", "answer": "A3"}
            ]
        ]
        
        retriever = KnowledgeRetriever(
            qdrant_manager=mock_qdrant_manager,
            embedding_engine=mock_embedding_engine
        )
        
        chat_type_id = uuid4()
        chunks = retriever.search_many(
            chat_type_id=chat_type_id,
            queries=["query1", "query2"],
            limit_per_query=5
        )
        
        assert len(chunks) == 3
        chunk_ids = [c["id"] for c in chunks]
        assert chunk_ids == ["chunk_1", "chunk_2", "chunk_3"]
    
    def test_search_many_with_error(self, mock_qdrant_manager, mock_embedding_engine):
        mock_qdrant_manager.search.side_effect = [
            [{"id": "chunk_1", "score": 0.95, "question": "Q1", "answer": "A1"}],
            Exception("Search error"),
            [{"id": "chunk_2", "score": 0.85, "question": "Q2", "answer": "A2"}]
        ]
        
        retriever = KnowledgeRetriever(
            qdrant_manager=mock_qdrant_manager,
            embedding_engine=mock_embedding_engine
        )
        
        chat_type_id = uuid4()
        chunks = retriever.search_many(
            chat_type_id=chat_type_id,
            queries=["query1", "query2", "query3"],
            limit_per_query=5
        )
        
        assert len(chunks) == 2
        chunk_ids = [c["id"] for c in chunks]
        assert "chunk_1" in chunk_ids
        assert "chunk_2" in chunk_ids
