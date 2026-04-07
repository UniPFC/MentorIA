import pytest
from unittest.mock import MagicMock
from src.rag.engine.reranker import RerankerEngine


@pytest.mark.unit
class TestRerankerEngine:
    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.rerank.return_value = [0.9, 0.7, 0.5, 0.3]
        return provider
    
    def test_init(self, mock_provider):
        engine = RerankerEngine(mock_provider)
        
        assert engine.provider == mock_provider
    
    def test_rerank_chunks_empty_list(self, mock_provider):
        engine = RerankerEngine(mock_provider)
        
        result = engine.rerank_chunks("query", [])
        
        assert result == []
        mock_provider.rerank.assert_not_called()
    
    def test_rerank_chunks_success(self, mock_provider):
        engine = RerankerEngine(mock_provider)
        
        chunks = [
            {"id": "1", "question": "Q1", "answer": "A1"},
            {"id": "2", "question": "Q2", "answer": "A2"},
            {"id": "3", "question": "Q3", "answer": "A3"},
            {"id": "4", "question": "Q4", "answer": "A4"}
        ]
        
        result = engine.rerank_chunks("test query", chunks, top_k=2, threshold=0.6)
        
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[0]["rerank_score"] == 0.9
        assert result[1]["id"] == "2"
        assert result[1]["rerank_score"] == 0.7
        
        mock_provider.rerank.assert_called_once()
        call_args = mock_provider.rerank.call_args[0]
        assert call_args[0] == "test query"
        assert len(call_args[1]) == 4
    
    def test_rerank_chunks_with_threshold(self, mock_provider):
        engine = RerankerEngine(mock_provider)
        
        chunks = [
            {"id": "1", "question": "Q1", "answer": "A1"},
            {"id": "2", "question": "Q2", "answer": "A2"},
            {"id": "3", "question": "Q3", "answer": "A3"},
            {"id": "4", "question": "Q4", "answer": "A4"}
        ]
        
        result = engine.rerank_chunks("test query", chunks, top_k=10, threshold=0.6)
        
        assert len(result) == 2
        assert all(chunk["rerank_score"] >= 0.6 for chunk in result)
    
    def test_rerank_chunks_sorted_by_score(self, mock_provider):
        mock_provider.rerank.return_value = [0.5, 0.9, 0.3, 0.7]
        engine = RerankerEngine(mock_provider)
        
        chunks = [
            {"id": "1", "question": "Q1", "answer": "A1"},
            {"id": "2", "question": "Q2", "answer": "A2"},
            {"id": "3", "question": "Q3", "answer": "A3"},
            {"id": "4", "question": "Q4", "answer": "A4"}
        ]
        
        result = engine.rerank_chunks("test query", chunks, top_k=10, threshold=0.0)
        
        assert len(result) == 4
        assert result[0]["id"] == "2"
        assert result[0]["rerank_score"] == 0.9
        assert result[1]["id"] == "4"
        assert result[1]["rerank_score"] == 0.7
        assert result[2]["id"] == "1"
        assert result[2]["rerank_score"] == 0.5
        assert result[3]["id"] == "3"
        assert result[3]["rerank_score"] == 0.3
    
    def test_rerank_chunks_top_k_limit(self, mock_provider):
        mock_provider.rerank.return_value = [0.9, 0.8, 0.7, 0.6, 0.5]
        engine = RerankerEngine(mock_provider)
        
        chunks = [
            {"id": str(i), "question": f"Q{i}", "answer": f"A{i}"}
            for i in range(5)
        ]
        
        result = engine.rerank_chunks("test query", chunks, top_k=3, threshold=0.0)
        
        assert len(result) == 3
        assert result[0]["rerank_score"] == 0.9
        assert result[1]["rerank_score"] == 0.8
        assert result[2]["rerank_score"] == 0.7
    
    def test_rerank_chunks_all_filtered_by_threshold(self, mock_provider):
        mock_provider.rerank.return_value = [0.3, 0.2, 0.1]
        engine = RerankerEngine(mock_provider)
        
        chunks = [
            {"id": "1", "question": "Q1", "answer": "A1"},
            {"id": "2", "question": "Q2", "answer": "A2"},
            {"id": "3", "question": "Q3", "answer": "A3"}
        ]
        
        result = engine.rerank_chunks("test query", chunks, top_k=10, threshold=0.5)
        
        assert len(result) == 0
    
    def test_rerank_chunks_error_handling(self, mock_provider):
        mock_provider.rerank.side_effect = Exception("Rerank error")
        engine = RerankerEngine(mock_provider)
        
        chunks = [
            {"id": "1", "question": "Q1", "answer": "A1"}
        ]
        
        with pytest.raises(Exception, match="Rerank error"):
            engine.rerank_chunks("test query", chunks)
    
    def test_rerank_chunks_document_format(self, mock_provider):
        engine = RerankerEngine(mock_provider)
        
        chunks = [
            {"id": "1", "question": "What is AI?", "answer": "Artificial Intelligence"}
        ]
        
        engine.rerank_chunks("test query", chunks)
        
        call_args = mock_provider.rerank.call_args[0]
        documents = call_args[1]
        assert documents[0] == "What is AI?\n\nArtificial Intelligence"
