import pytest
import torch
from unittest.mock import MagicMock, patch
from src.ai.provider.reranker import HFRerankProvider


@pytest.mark.unit
class TestHFRerankProvider:
    def test_init(self):
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "[EOS]"
        
        provider = HFRerankProvider(mock_model, mock_tokenizer)
        
        assert provider.model == mock_model
        assert provider.tokenizer == mock_tokenizer
        mock_model.eval.assert_called_once()
        assert mock_tokenizer.pad_token == "[EOS]"
    
    def test_init_no_pad_token_no_eos(self):
        mock_model = MagicMock()
        mock_model.config.pad_token_id = None
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = None
        mock_tokenizer.pad_token_id = 0
        
        provider = HFRerankProvider(mock_model, mock_tokenizer)
        
        assert provider.model == mock_model
        assert mock_model.config.pad_token_id == 0
    
    def test_rerank_success(self):
        mock_model = MagicMock()
        mock_model.device = 'cpu'
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = "[PAD]"
        
        mock_encoded = {
            'input_ids': torch.tensor([[1, 2, 3], [4, 5, 6]]),
            'attention_mask': torch.tensor([[1, 1, 1], [1, 1, 1]])
        }
        mock_tokenizer.return_value.to.return_value = mock_encoded
        
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([0.8, 0.6])
        mock_model.return_value = mock_output
        
        provider = HFRerankProvider(mock_model, mock_tokenizer)
        result = provider.rerank("query", ["doc1", "doc2"])
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(0 <= score <= 1 for score in result)
        mock_tokenizer.assert_called_once()
        mock_model.assert_called_once()
    
    def test_rerank_with_batch_size(self):
        mock_model = MagicMock()
        mock_model.device = 'cpu'
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = "[PAD]"
        
        def mock_tokenizer_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.to.return_value = {
                'input_ids': torch.tensor([[1, 2]]),
                'attention_mask': torch.tensor([[1, 1]])
            }
            return mock_result
        
        mock_tokenizer.side_effect = mock_tokenizer_side_effect
        
        mock_output1 = MagicMock()
        mock_output1.logits = torch.tensor([0.9])
        mock_output2 = MagicMock()
        mock_output2.logits = torch.tensor([0.7])
        
        mock_model.side_effect = [mock_output1, mock_output2]
        
        provider = HFRerankProvider(mock_model, mock_tokenizer)
        result = provider.rerank("query", ["doc1", "doc2"], batch_size=1)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert mock_model.call_count == 2
    
    def test_rerank_with_max_length(self):
        mock_model = MagicMock()
        mock_model.device = 'cpu'
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = "[PAD]"
        
        mock_encoded = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_tokenizer.return_value.to.return_value = mock_encoded
        
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([0.8])
        mock_model.return_value = mock_output
        
        provider = HFRerankProvider(mock_model, mock_tokenizer)
        result = provider.rerank("query", ["doc1"], max_length=512)
        
        call_kwargs = mock_tokenizer.call_args[1]
        assert call_kwargs['max_length'] == 512
    
    def test_rerank_empty_documents(self):
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        
        provider = HFRerankProvider(mock_model, mock_tokenizer)
        result = provider.rerank("query", [])
        
        assert result == []
        mock_tokenizer.assert_not_called()
    
    def test_rerank_logits_2d_single_column(self):
        mock_model = MagicMock()
        mock_model.device = 'cpu'
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = "[PAD]"
        
        mock_encoded = {
            'input_ids': torch.tensor([[1, 2]]),
            'attention_mask': torch.tensor([[1, 1]])
        }
        mock_tokenizer.return_value.to.return_value = mock_encoded
        
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([[0.8]])
        mock_model.return_value = mock_output
        
        provider = HFRerankProvider(mock_model, mock_tokenizer)
        result = provider.rerank("query", ["doc1"])
        
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_rerank_logits_2d_multi_column(self):
        mock_model = MagicMock()
        mock_model.device = 'cpu'
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = "[PAD]"
        
        mock_encoded = {
            'input_ids': torch.tensor([[1, 2]]),
            'attention_mask': torch.tensor([[1, 1]])
        }
        mock_tokenizer.return_value.to.return_value = mock_encoded
        
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([[0.1, 0.8]])
        mock_model.return_value = mock_output
        
        provider = HFRerankProvider(mock_model, mock_tokenizer)
        result = provider.rerank("query", ["doc1"])
        
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_rerank_error_handling(self):
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = "[PAD]"
        mock_tokenizer.side_effect = Exception("Tokenization error")
        
        provider = HFRerankProvider(mock_model, mock_tokenizer)
        
        with pytest.raises(Exception, match="Tokenization error"):
            provider.rerank("query", ["doc1", "doc2"])
