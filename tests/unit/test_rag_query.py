import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from src.rag.engine.query import QueryEngine
from src.rag.models.query import RAGQuery


@pytest.mark.unit
class TestQueryEngine:
    @pytest.fixture
    def mock_llm_provider(self):
        provider = MagicMock()
        provider.model_name = "test-model"
        provider.generate.return_value = "Rewritten: What is artificial intelligence?"
        provider.generate_structured.return_value = MagicMock(queries=[
            RAGQuery(text="What is AI?"),
            RAGQuery(text="Define artificial intelligence")
        ])
        return provider
        
    @patch('src.rag.engine.query.settings')
    def test_contextualize_query_with_history(self, mock_settings, mock_llm_provider):
        mock_settings.BASE_DIR = "."
        mock_settings.LLM_MODEL = "test-model"
        mock_settings.LLM_PROVIDER = "test"
        
        with patch('builtins.open', MagicMock()):
            with patch('src.rag.engine.query.QueryEngine._load_prompt', return_value="Test prompt {chat_history} {query_text}"):
                engine = QueryEngine(primary_provider=mock_llm_provider)
                
                chat_history = [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"}
                ]
                
                result = engine.contextualize_query("What is AI?", chat_history)
                
                assert "artificial intelligence" in result.lower()
                mock_llm_provider.generate.assert_called_once()
        
    @patch('src.rag.engine.query.settings')
    def test_contextualize_query_no_history(self, mock_settings, mock_llm_provider):
        mock_settings.BASE_DIR = "."
        mock_settings.LLM_MODEL = "test-model"
        mock_settings.LLM_PROVIDER = "test"
        
        with patch('builtins.open', MagicMock()):
            with patch('src.rag.engine.query.QueryEngine._load_prompt', return_value="Test prompt"):
                engine = QueryEngine(primary_provider=mock_llm_provider)
                
                result = engine.contextualize_query("What is AI?", [])
                
                assert result == "What is AI?"
                mock_llm_provider.generate.assert_not_called()
        
    @patch('src.rag.engine.query.settings')
    def test_expand_query(self, mock_settings, mock_llm_provider):
        mock_settings.BASE_DIR = "."
        mock_settings.LLM_MODEL = "test-model"
        mock_settings.LLM_PROVIDER = "test"
        mock_settings.QUERY_EXPANSION_COUNT = 3
        
        def mock_load_prompt(name):
            if 'system' in name:
                return "System prompt with {count}"
            return "User prompt with {query_text} and {count}"
        
        with patch('builtins.open', MagicMock()):
            with patch.object(QueryEngine, '_load_prompt', side_effect=mock_load_prompt):
                engine = QueryEngine(primary_provider=mock_llm_provider)
                
                result = engine.expand_query("What is AI?")
                
                assert len(result) >= 1
                assert any("AI" in q.text for q in result)
                
    @patch('src.rag.engine.query.settings')
    def test_expand_query_fallback(self, mock_settings, mock_llm_provider):
        mock_settings.BASE_DIR = "."
        mock_settings.LLM_MODEL = "test-model"
        mock_settings.LLM_PROVIDER = "test"
        mock_settings.QUERY_EXPANSION_COUNT = 3
        
        mock_llm_provider.generate_structured.side_effect = Exception("API Error")
        
        with patch('builtins.open', MagicMock()):
            with patch('src.rag.engine.query.QueryEngine._load_prompt', return_value="Test prompt"):
                engine = QueryEngine(primary_provider=mock_llm_provider)
                
                result = engine.expand_query("What is AI?")
                
                assert len(result) == 1
                assert result[0].text == "What is AI?"
    
    @patch('src.rag.engine.query.settings')
    def test_load_prompt_file_not_found(self, mock_settings, mock_llm_provider):
        mock_settings.BASE_DIR = "."
        
        with patch('builtins.open', MagicMock()):
            with patch('src.rag.engine.query.QueryEngine._load_prompt', return_value="Test"):
                engine = QueryEngine(primary_provider=mock_llm_provider)
        
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                engine._load_prompt("nonexistent_prompt")
    
    @patch('src.rag.engine.query.settings')
    def test_load_prompt_general_error(self, mock_settings, mock_llm_provider):
        mock_settings.BASE_DIR = "."
        
        with patch('builtins.open', MagicMock()):
            with patch('src.rag.engine.query.QueryEngine._load_prompt', return_value="Test"):
                engine = QueryEngine(primary_provider=mock_llm_provider)
        
        with patch('builtins.open', side_effect=Exception("Read error")):
            with pytest.raises(Exception, match="Read error"):
                engine._load_prompt("test_prompt")
    
    @patch('src.rag.engine.query.settings')
    def test_contextualize_query_error_fallback(self, mock_settings, mock_llm_provider):
        mock_settings.BASE_DIR = "."
        
        mock_llm_provider.generate.side_effect = Exception("Generation error")
        
        with patch('builtins.open', MagicMock()):
            with patch('src.rag.engine.query.QueryEngine._load_prompt', return_value="Test prompt"):
                engine = QueryEngine(primary_provider=mock_llm_provider)
                
                chat_history = [{"role": "user", "content": "Hello"}]
                result = engine.contextualize_query("What is AI?", chat_history)
                
                assert result == "What is AI?"
    
    @patch('src.rag.engine.query.settings')
    def test_normalize_response_deduplication(self, mock_settings, mock_llm_provider):
        mock_settings.BASE_DIR = "."
        mock_settings.QUERY_EXPANSION_COUNT = 5
        
        with patch('builtins.open', MagicMock()):
            with patch('src.rag.engine.query.QueryEngine._load_prompt', return_value="Test"):
                engine = QueryEngine(primary_provider=mock_llm_provider)
                
                variations = [
                    RAGQuery(text="What is AI?"),
                    RAGQuery(text="what is ai?"),
                    RAGQuery(text="Define AI"),
                    RAGQuery(text="What is artificial intelligence?")
                ]
                
                result = engine._normalize_response("What is AI?", variations)
                
                assert len(result) <= 5
                texts = [q.text.lower() for q in result]
                assert len(texts) == len(set(texts))
    
    @patch('src.rag.engine.query.settings')
    def test_normalize_response_limit(self, mock_settings, mock_llm_provider):
        mock_settings.BASE_DIR = "."
        mock_settings.QUERY_EXPANSION_COUNT = 2
        
        with patch('builtins.open', MagicMock()):
            with patch('src.rag.engine.query.QueryEngine._load_prompt', return_value="Test"):
                engine = QueryEngine(primary_provider=mock_llm_provider)
                
                variations = [
                    RAGQuery(text="Query 1"),
                    RAGQuery(text="Query 2"),
                    RAGQuery(text="Query 3"),
                    RAGQuery(text="Query 4")
                ]
                
                result = engine._normalize_response("Original", variations)
                
                assert len(result) == 2
    
    @patch('src.rag.engine.query.settings')
    def test_expand_query_unstructured_response(self, mock_settings, mock_llm_provider):
        mock_settings.BASE_DIR = "."
        mock_settings.QUERY_EXPANSION_COUNT = 3
        
        mock_llm_provider.generate_structured.return_value = "Unstructured string response"
        
        with patch('builtins.open', MagicMock()):
            with patch('src.rag.engine.query.QueryEngine._load_prompt', return_value="Test"):
                engine = QueryEngine(primary_provider=mock_llm_provider)
                
                result = engine.expand_query("What is AI?")
                
                assert len(result) == 1
                assert result[0].text == "What is AI?"
