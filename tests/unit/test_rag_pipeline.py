import pytest
from unittest.mock import MagicMock, patch, mock_open
from uuid import uuid4
from src.rag.pipeline import RAGPipeline


@pytest.mark.unit
class TestRAGPipeline:
    @pytest.fixture
    def mock_settings(self):
        with patch('src.rag.pipeline.settings') as mock_settings:
            mock_settings.BASE_DIR = "."
            mock_settings.LLM_MODEL = "test-model"
            mock_settings.LLM_PROVIDER = "test"
            mock_settings.EMBEDDING_MODEL_ID = "test-embedding"
            mock_settings.RERANKER_MODEL_ID = "test-reranker"
            mock_settings.K_RETRIEVAL = 10
            mock_settings.TOP_K = 5
            mock_settings.THRESHOLD = 0.5
            yield mock_settings
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_singleton_pattern(self, mock_reranker, mock_retriever, mock_query, mock_qdrant, mock_loader, mock_provider, mock_settings):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        RAGPipeline._instance = None
        
        pipeline1 = RAGPipeline()
        pipeline2 = RAGPipeline()
        
        assert pipeline1 is pipeline2
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_initialization(self, mock_reranker, mock_retriever, mock_query, mock_qdrant, mock_loader, mock_provider, mock_settings):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        RAGPipeline._instance = None
        
        pipeline = RAGPipeline()
        
        assert pipeline._initialized is True
        mock_provider.assert_called_once()
        mock_loader_instance.load_embedding.assert_called_once()
        mock_loader_instance.load_reranker.assert_called_once()
    
    @patch('builtins.open', new_callable=mock_open, read_data='Test prompt')
    def test_load_prompt_success(self, mock_file, mock_settings):
        result = RAGPipeline._load_prompt("test_prompt")
        
        assert result == "Test prompt"
        mock_file.assert_called_once()
    
    @patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    def test_load_prompt_file_not_found(self, mock_file, mock_settings):
        with pytest.raises(FileNotFoundError):
            RAGPipeline._load_prompt("nonexistent")
    
    @patch('builtins.open', side_effect=Exception("Read error"))
    def test_load_prompt_general_error(self, mock_file, mock_settings):
        with pytest.raises(Exception, match="Read error"):
            RAGPipeline._load_prompt("test")
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_run_success(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_query_instance = MagicMock()
        mock_query_class.return_value = mock_query_instance
        mock_query_instance.expand_query.return_value = [MagicMock(text="query1"), MagicMock(text="query2")]
        
        mock_retriever_instance = MagicMock()
        mock_retriever_class.return_value = mock_retriever_instance
        mock_retriever_instance.search_many.return_value = [
            {"id": "1", "score": 0.9, "question": "Q1", "answer": "A1"}
        ]
        
        mock_reranker_instance = MagicMock()
        mock_reranker_class.return_value = mock_reranker_instance
        mock_reranker_instance.rerank_chunks.return_value = [
            {"id": "1", "score": 0.95, "question": "Q1", "answer": "A1"}
        ]
        
        mock_provider_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_provider_instance.generate.return_value = "Generated answer"
        
        with patch.object(RAGPipeline, '_generate_answer', return_value="Generated answer"):
            pipeline = RAGPipeline()
            
            result = pipeline.run(
                chat_type_id=uuid4(),
                query="What is AI?"
            )
        
        assert result["answer"] == "Generated answer"
        assert len(result["chunks"]) == 1
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_run_no_chunks_retrieved(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_query_instance = MagicMock()
        mock_query_class.return_value = mock_query_instance
        mock_query_instance.expand_query.return_value = [MagicMock(text="query1")]
        
        mock_retriever_instance = MagicMock()
        mock_retriever_class.return_value = mock_retriever_instance
        mock_retriever_instance.search_many.return_value = []
        
        pipeline = RAGPipeline()
        
        result = pipeline.run(
            chat_type_id=uuid4(),
            query="What is AI?"
        )
        
        assert "não encontrei informações relevantes" in result["answer"]
        assert result["chunks"] == []
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_run_all_chunks_filtered_by_reranker(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_query_instance = MagicMock()
        mock_query_class.return_value = mock_query_instance
        mock_query_instance.expand_query.return_value = [MagicMock(text="query1")]
        
        mock_retriever_instance = MagicMock()
        mock_retriever_class.return_value = mock_retriever_instance
        mock_retriever_instance.search_many.return_value = [
            {"id": "1", "score": 0.3, "question": "Q1", "answer": "A1"}
        ]
        
        mock_reranker_instance = MagicMock()
        mock_reranker_class.return_value = mock_reranker_instance
        mock_reranker_instance.rerank_chunks.return_value = []
        
        pipeline = RAGPipeline()
        
        result = pipeline.run(
            chat_type_id=uuid4(),
            query="What is AI?"
        )
        
        assert "não eram relevantes o suficiente" in result["answer"]
        assert result["chunks"] == []
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_run_with_chat_history(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_query_instance = MagicMock()
        mock_query_class.return_value = mock_query_instance
        mock_query_instance.contextualize_query.return_value = "Contextualized query"
        mock_query_instance.expand_query.return_value = [MagicMock(text="query1")]
        
        mock_retriever_instance = MagicMock()
        mock_retriever_class.return_value = mock_retriever_instance
        mock_retriever_instance.search_many.return_value = [
            {"id": "1", "score": 0.9, "question": "Q1", "answer": "A1"}
        ]
        
        mock_reranker_instance = MagicMock()
        mock_reranker_class.return_value = mock_reranker_instance
        mock_reranker_instance.rerank_chunks.return_value = [
            {"id": "1", "score": 0.95, "question": "Q1", "answer": "A1"}
        ]
        
        with patch.object(RAGPipeline, '_generate_answer', return_value="Answer"):
            pipeline = RAGPipeline()
            
            result = pipeline.run(
                chat_type_id=uuid4(),
                query="What is AI?",
                chat_history=[{"role": "user", "content": "Hello"}]
            )
        
        mock_query_instance.contextualize_query.assert_called_once()
        assert result["answer"] == "Answer"
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_run_error_handling(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_query_instance = MagicMock()
        mock_query_class.return_value = mock_query_instance
        mock_query_instance.expand_query.side_effect = Exception("Query expansion error")
        
        pipeline = RAGPipeline()
        
        with pytest.raises(Exception, match="Query expansion error"):
            pipeline.run(
                chat_type_id=uuid4(),
                query="What is AI?"
            )
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_run_stream_success(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_query_instance = MagicMock()
        mock_query_class.return_value = mock_query_instance
        mock_query_instance.expand_query.return_value = [MagicMock(text="query1")]
        
        mock_retriever_instance = MagicMock()
        mock_retriever_class.return_value = mock_retriever_instance
        mock_retriever_instance.search_many.return_value = [
            {"id": "1", "score": 0.9, "question": "Q1", "answer": "A1"}
        ]
        
        mock_reranker_instance = MagicMock()
        mock_reranker_class.return_value = mock_reranker_instance
        mock_reranker_instance.rerank_chunks.return_value = [
            {"id": "1", "score": 0.95, "question": "Q1", "answer": "A1", "rerank_score": 0.95}
        ]
        
        mock_provider_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_provider_instance.generate_stream.return_value = iter(["Hello", " ", "world"])
        
        with patch.object(RAGPipeline, '_load_prompt', return_value="System: {context}"):
            pipeline = RAGPipeline()
            
            results = list(pipeline.run_stream(
                chat_type_id=uuid4(),
                query="What is AI?"
            ))
        
        assert any(r["type"] == "sources" for r in results)
        assert any(r["type"] == "token" for r in results)
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_run_stream_no_chunks(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_query_instance = MagicMock()
        mock_query_class.return_value = mock_query_instance
        mock_query_instance.expand_query.return_value = [MagicMock(text="query1")]
        
        mock_retriever_instance = MagicMock()
        mock_retriever_class.return_value = mock_retriever_instance
        mock_retriever_instance.search_many.return_value = []
        
        pipeline = RAGPipeline()
        
        results = list(pipeline.run_stream(
            chat_type_id=uuid4(),
            query="What is AI?"
        ))
        
        assert len(results) == 1
        assert results[0]["type"] == "error"
        assert "não encontrei informações relevantes" in results[0]["content"]
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_run_stream_all_filtered(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_query_instance = MagicMock()
        mock_query_class.return_value = mock_query_instance
        mock_query_instance.expand_query.return_value = [MagicMock(text="query1")]
        
        mock_retriever_instance = MagicMock()
        mock_retriever_class.return_value = mock_retriever_instance
        mock_retriever_instance.search_many.return_value = [
            {"id": "1", "score": 0.3, "question": "Q1", "answer": "A1"}
        ]
        
        mock_reranker_instance = MagicMock()
        mock_reranker_class.return_value = mock_reranker_instance
        mock_reranker_instance.rerank_chunks.return_value = []
        
        pipeline = RAGPipeline()
        
        results = list(pipeline.run_stream(
            chat_type_id=uuid4(),
            query="What is AI?"
        ))
        
        assert len(results) == 1
        assert results[0]["type"] == "error"
        assert "não eram relevantes o suficiente" in results[0]["content"]
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_run_stream_error(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_query_instance = MagicMock()
        mock_query_class.return_value = mock_query_instance
        mock_query_instance.expand_query.side_effect = Exception("Test error")
        
        pipeline = RAGPipeline()
        
        results = list(pipeline.run_stream(
            chat_type_id=uuid4(),
            query="What is AI?"
        ))
        
        assert len(results) == 1
        assert results[0]["type"] == "error"
        assert "Erro no processamento" in results[0]["content"]
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_generate_answer_stream_error(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_provider_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_provider_instance.generate_stream.side_effect = Exception("Stream error")
        
        with patch.object(RAGPipeline, '_load_prompt', return_value="System: {context}"):
            pipeline = RAGPipeline()
            
            chunks = [{"question": "Q1", "answer": "A1"}]
            results = list(pipeline._generate_answer_stream("query", chunks))
        
        assert len(results) == 1
        assert results[0]["type"] == "error"
        assert "Erro ao gerar resposta" in results[0]["content"]
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_generate_answer_with_history(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_provider_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_provider_instance.generate.return_value = "Generated answer"
        
        with patch.object(RAGPipeline, '_load_prompt', return_value="System: {context}"):
            pipeline = RAGPipeline()
            
            chunks = [{"question": "Q1", "answer": "A1"}]
            chat_history = [{"role": "user", "content": "Hello"}]
            
            answer = pipeline._generate_answer("query", chunks, chat_history)
        
        assert answer == "Generated answer"
        call_args = mock_provider_instance.generate.call_args[0][0]
        assert len(call_args) == 3
        assert call_args[0]["role"] == "system"
        assert call_args[1]["role"] == "user"
        assert call_args[2]["role"] == "user"
    
    @patch('src.rag.pipeline.Provider')
    @patch('src.rag.pipeline.ModelLoader')
    @patch('src.rag.pipeline.QdrantManager')
    @patch('src.rag.pipeline.QueryEngine')
    @patch('src.rag.pipeline.KnowledgeRetriever')
    @patch('src.rag.pipeline.RerankerEngine')
    def test_generate_answer_error(self, mock_reranker_class, mock_retriever_class, mock_query_class, mock_qdrant, mock_loader, mock_provider, mock_settings):
        RAGPipeline._instance = None
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        mock_loader_instance.load_reranker.return_value = (MagicMock(), MagicMock())
        
        mock_provider_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_provider_instance.generate.side_effect = Exception("Generation error")
        
        with patch.object(RAGPipeline, '_load_prompt', return_value="System: {context}"):
            pipeline = RAGPipeline()
            
            chunks = [{"question": "Q1", "answer": "A1"}]
            answer = pipeline._generate_answer("query", chunks)
        
        assert "ocorreu um erro" in answer
