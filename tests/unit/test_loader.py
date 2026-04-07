import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.ai.loader import ModelLoader
import torch


@pytest.mark.unit
class TestModelLoader:
    @pytest.fixture
    def mock_settings(self):
        with patch('src.ai.loader.settings') as mock_settings:
            mock_settings.CACHE_DIR = "/tmp/cache"
            mock_settings.HUGGINGFACE_TOKEN = None
            yield mock_settings
    
    def test_init(self, mock_settings):
        with patch('torch.cuda.is_available', return_value=False):
            loader = ModelLoader()
            
            assert loader.device == "cpu"
            assert loader.cache_dir is not None
            
    def test_init_cuda_available(self, mock_settings):
        with patch('torch.cuda.is_available', return_value=True):
            loader = ModelLoader()
            
            assert loader.device == "cuda"
            
    def test_get_quantization_config_4bit(self, mock_settings):
        with patch('torch.cuda.is_available', return_value=True):
            loader = ModelLoader()
            config = loader._get_quantization_config("4bit")
            
            assert config is not None
            assert config.load_in_4bit is True
            
    def test_get_quantization_config_8bit(self, mock_settings):
        with patch('torch.cuda.is_available', return_value=True):
            loader = ModelLoader()
            config = loader._get_quantization_config("8bit")
            
            assert config is not None
            assert config.load_in_8bit is True
            
    def test_get_quantization_config_none(self, mock_settings):
        with patch('torch.cuda.is_available', return_value=False):
            loader = ModelLoader()
            config = loader._get_quantization_config(None)
            
            assert config is None
            
    @patch('src.ai.loader.AutoModel')
    @patch('src.ai.loader.AutoTokenizer')
    def test_load_embedding(self, mock_tokenizer_class, mock_model_class, mock_settings):
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        mock_model.to.return_value = mock_model
        
        with patch('torch.cuda.is_available', return_value=False):
            loader = ModelLoader()
            model, tokenizer = loader.load_embedding("test/model")
            
            assert model is not None
            assert tokenizer is not None
            mock_model.eval.assert_called_once()
            
    @patch('src.ai.loader.AutoModelForSequenceClassification')
    @patch('src.ai.loader.AutoTokenizer')
    def test_load_reranker(self, mock_tokenizer_class, mock_model_class, mock_settings):
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        mock_model.to.return_value = mock_model
        
        with patch('torch.cuda.is_available', return_value=False):
            loader = ModelLoader()
            model, tokenizer = loader.load_reranker("test/reranker")
            
            assert model is not None
            assert tokenizer is not None
            mock_model.eval.assert_called_once()
            
    @patch('src.ai.loader.AutoModelForCausalLM')
    @patch('src.ai.loader.AutoTokenizer')
    def test_load_llm(self, mock_tokenizer_class, mock_model_class, mock_settings):
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "<eos>"
        mock_model = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model
        
        with patch('torch.cuda.is_available', return_value=False):
            loader = ModelLoader()
            model, tokenizer = loader.load_llm("test/llm")
            
            assert model is not None
            assert tokenizer is not None
            assert tokenizer.pad_token == "<eos>"
            
    def test_unload_memory_cuda(self, mock_settings):
        with patch('torch.cuda.is_available', return_value=True):
            with patch('torch.cuda.empty_cache') as mock_empty_cache:
                loader = ModelLoader()
                loader.unload_memory()
                
                mock_empty_cache.assert_called_once()
                
    def test_unload_memory_cpu(self, mock_settings):
        with patch('torch.cuda.is_available', return_value=False):
            loader = ModelLoader()
            loader.unload_memory()
    
    @patch('src.ai.loader.AutoModel')
    @patch('src.ai.loader.AutoTokenizer')
    def test_load_embedding_error(self, mock_tokenizer_class, mock_model_class, mock_settings):
        mock_model_class.from_pretrained.side_effect = Exception("Model load error")
        
        with patch('torch.cuda.is_available', return_value=False):
            loader = ModelLoader()
            
            with pytest.raises(Exception, match="Model load error"):
                loader.load_embedding("test/model")
    
    @patch('src.ai.loader.AutoModelForSequenceClassification')
    @patch('src.ai.loader.AutoTokenizer')
    def test_load_reranker_error(self, mock_tokenizer_class, mock_model_class, mock_settings):
        mock_model_class.from_pretrained.side_effect = Exception("Reranker load error")
        
        with patch('torch.cuda.is_available', return_value=False):
            loader = ModelLoader()
            
            with pytest.raises(Exception, match="Reranker load error"):
                loader.load_reranker("test/reranker")
    
    @patch('src.ai.loader.AutoModelForCausalLM')
    @patch('src.ai.loader.AutoTokenizer')
    def test_load_llm_error(self, mock_tokenizer_class, mock_model_class, mock_settings):
        mock_model_class.from_pretrained.side_effect = Exception("LLM load error")
        
        with patch('torch.cuda.is_available', return_value=False):
            loader = ModelLoader()
            
            with pytest.raises(Exception, match="LLM load error"):
                loader.load_llm("test/llm")
