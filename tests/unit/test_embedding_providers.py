import pytest
import torch
from unittest.mock import MagicMock, patch, Mock
from src.ai.provider.embedding import HFEmbeddingProvider, RemoteEmbeddingProvider


@pytest.mark.unit
class TestHFEmbeddingProvider:
    def test_init(self):
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        
        provider = HFEmbeddingProvider(mock_model, mock_tokenizer)
        
        assert provider.model == mock_model
        assert provider.tokenizer == mock_tokenizer
        mock_model.eval.assert_called_once()
    
    def test_embed_success(self):
        mock_model = MagicMock()
        mock_model.device = 'cpu'
        mock_tokenizer = MagicMock()
        
        mock_encoded = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_tokenizer.return_value.to.return_value = mock_encoded
        
        mock_output = (torch.randn(1, 3, 384),)
        mock_model.return_value = mock_output
        
        provider = HFEmbeddingProvider(mock_model, mock_tokenizer)
        result = provider.embed(["test text"])
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        mock_tokenizer.assert_called_once()
    
    def test_embed_with_max_length(self):
        mock_model = MagicMock()
        mock_model.device = 'cpu'
        mock_tokenizer = MagicMock()
        
        mock_encoded = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_tokenizer.return_value.to.return_value = mock_encoded
        
        mock_output = (torch.randn(1, 3, 384),)
        mock_model.return_value = mock_output
        
        provider = HFEmbeddingProvider(mock_model, mock_tokenizer)
        result = provider.embed(["test text"], max_length=512)
        
        assert isinstance(result, list)
        call_kwargs = mock_tokenizer.call_args[1]
        assert call_kwargs['max_length'] == 512
    
    def test_embed_error_handling(self):
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.side_effect = Exception("Tokenization error")
        
        provider = HFEmbeddingProvider(mock_model, mock_tokenizer)
        
        with pytest.raises(Exception, match="Tokenization error"):
            provider.embed(["test text"])
    
    def test_mean_pooling(self):
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        
        provider = HFEmbeddingProvider(mock_model, mock_tokenizer)
        
        model_output = (torch.randn(2, 3, 384),)
        attention_mask = torch.ones(2, 3)
        
        result = provider._mean_pooling(model_output, attention_mask)
        
        assert result.shape == (2, 384)


@pytest.mark.unit
class TestRemoteEmbeddingProvider:
    @patch('src.ai.provider.embedding.resolve_api_key')
    @patch('src.ai.provider.embedding.OpenAI')
    def test_init_with_defaults(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        provider = RemoteEmbeddingProvider("text-embedding-ada-002")
        
        assert provider.model_name == "text-embedding-ada-002"
        mock_resolve_key.assert_called_once_with("openai", None)
        mock_openai.assert_called_once()
    
    @patch('src.ai.provider.embedding.resolve_api_key')
    @patch('src.ai.provider.embedding.OpenAI')
    def test_init_with_custom_url(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        provider = RemoteEmbeddingProvider(
            "custom-model",
            provider_alias="custom",
            base_url="https://custom.api.com"
        )
        
        assert provider.target_url == "https://custom.api.com"
        assert provider.model_name == "custom-model"
    
    @patch('src.ai.provider.embedding.resolve_api_key')
    @patch('src.ai.provider.embedding.OpenAI')
    def test_init_with_api_key(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "custom-key"
        
        provider = RemoteEmbeddingProvider(
            "model",
            api_key="custom-key"
        )
        
        mock_resolve_key.assert_called_once_with("openai", "custom-key")
    
    @patch('src.ai.provider.embedding.resolve_api_key')
    @patch('src.ai.provider.embedding.OpenAI')
    def test_embed_success(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_item1 = MagicMock()
        mock_item1.index = 0
        mock_item1.embedding = [0.1, 0.2, 0.3]
        mock_item2 = MagicMock()
        mock_item2.index = 1
        mock_item2.embedding = [0.4, 0.5, 0.6]
        mock_response.data = [mock_item2, mock_item1]
        
        mock_client.embeddings.create.return_value = mock_response
        
        provider = RemoteEmbeddingProvider("text-embedding-ada-002")
        result = provider.embed(["text1", "text2"])
        
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]
        mock_client.embeddings.create.assert_called_once()
    
    @patch('src.ai.provider.embedding.resolve_api_key')
    @patch('src.ai.provider.embedding.OpenAI')
    def test_embed_with_kwargs(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_item = MagicMock()
        mock_item.index = 0
        mock_item.embedding = [0.1, 0.2]
        mock_response.data = [mock_item]
        
        mock_client.embeddings.create.return_value = mock_response
        
        provider = RemoteEmbeddingProvider("model")
        result = provider.embed(["text"], dimensions=512)
        
        call_kwargs = mock_client.embeddings.create.call_args[1]
        assert 'dimensions' in call_kwargs
        assert call_kwargs['dimensions'] == 512
    
    @patch('src.ai.provider.embedding.resolve_api_key')
    @patch('src.ai.provider.embedding.OpenAI')
    def test_embed_error_handling(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.embeddings.create.side_effect = Exception("API error")
        
        provider = RemoteEmbeddingProvider("model")
        
        with pytest.raises(Exception, match="API error"):
            provider.embed(["text"])
