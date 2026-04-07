import pytest
from unittest.mock import MagicMock, patch
from src.ai.embedding import EmbeddingEngine


@pytest.mark.unit
class TestEmbeddingEngine:
    def test_init(self, mock_embedding_provider):
        engine = EmbeddingEngine(mock_embedding_provider)
        
        assert engine.provider == mock_embedding_provider
        
    def test_embed_single_text(self, mock_embedding_provider):
        mock_embedding_provider.embed.return_value = [[0.1, 0.2, 0.3]]
        engine = EmbeddingEngine(mock_embedding_provider)
        
        result = engine.embed(["test text"])
        
        assert len(result) == 1
        assert len(result[0]) == 3
        mock_embedding_provider.embed.assert_called_once_with(["test text"])
        
    def test_embed_multiple_texts(self, mock_embedding_provider):
        mock_embedding_provider.embed.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ]
        engine = EmbeddingEngine(mock_embedding_provider)
        
        texts = ["text 1", "text 2"]
        result = engine.embed(texts)
        
        assert len(result) == 2
        assert len(result[0]) == 3
        assert len(result[1]) == 3
        mock_embedding_provider.embed.assert_called_once_with(texts)
        
    def test_embed_single(self, mock_embedding_provider):
        mock_embedding_provider.embed.return_value = [[0.1, 0.2, 0.3]]
        engine = EmbeddingEngine(mock_embedding_provider)
        
        result = engine.embed_single("test text")
        
        assert len(result) == 3
        assert result == [0.1, 0.2, 0.3]
        mock_embedding_provider.embed.assert_called_once_with(["test text"])
        
    def test_embed_with_kwargs(self, mock_embedding_provider):
        mock_embedding_provider.embed.return_value = [[0.1, 0.2, 0.3]]
        engine = EmbeddingEngine(mock_embedding_provider)
        
        result = engine.embed(["test"], batch_size=32, normalize=True)
        
        mock_embedding_provider.embed.assert_called_once_with(
            ["test"], 
            batch_size=32, 
            normalize=True
        )
