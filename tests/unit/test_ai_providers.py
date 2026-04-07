import pytest
from unittest.mock import MagicMock, patch
from src.ai.provider.base import EmbeddingProvider, LLMProvider, RerankProvider


@pytest.mark.unit
class TestBaseProviders:
    def test_embedding_provider_abstract(self):
        with pytest.raises(TypeError):
            EmbeddingProvider()
            
    def test_llm_provider_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider()
            
    def test_reranker_provider_abstract(self):
        with pytest.raises(TypeError):
            RerankProvider()


@pytest.mark.unit
class TestEmbeddingProviderImplementation:
    def test_custom_embedding_provider(self):
        class CustomEmbeddingProvider(EmbeddingProvider):
            def embed(self, inputs, **kwargs):
                return [[0.1] * 384 for _ in inputs]
                
        provider = CustomEmbeddingProvider()
        result = provider.embed(["text1", "text2"])
        
        assert len(result) == 2
        assert len(result[0]) == 384


@pytest.mark.unit
class TestLLMProviderImplementation:
    def test_custom_llm_provider(self):
        class CustomLLMProvider(LLMProvider):
            def generate(self, messages, **kwargs):
                return "Generated response"
                
            def stream(self, messages, **kwargs):
                return iter(["Generated ", "response"])
                
        provider = CustomLLMProvider()
        
        response = provider.generate([{"role": "user", "content": "Hello"}])
        assert response == "Generated response"
        
        stream = provider.stream([{"role": "user", "content": "Hello"}])
        chunks = list(stream)
        assert len(chunks) == 2


@pytest.mark.unit
class TestRerankProviderImplementation:
    def test_custom_rerank_provider(self):
        class CustomRerankProvider(RerankProvider):
            def rerank(self, query, documents, **kwargs):
                return [0.9, 0.8]
                
        provider = CustomRerankProvider()
        docs = ["doc1", "doc2"]
        
        result = provider.rerank("query", docs)
        
        assert len(result) == 2
        assert result[0] == 0.9
