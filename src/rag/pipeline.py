"""
RAG Pipeline for multi-tenant chat system.
Adapted from SoulsborneRAG to work with dynamic chat_type_id.
"""

import os
import threading
from typing import List, Dict, Any, Optional
from uuid import UUID
from config.logger import logger
from config.settings import settings
from src.rag.engine.retriever import KnowledgeRetriever
from src.rag.engine.reranker import RerankerEngine
from src.rag.engine.query import QueryEngine
from src.ai.provider.llm import Provider
from src.ai.loader import ModelLoader
from src.ai.provider.embedding import HFEmbeddingProvider, RemoteEmbeddingProvider
from src.ai.provider.reranker import HFRerankProvider
from src.ai.embedding import EmbeddingEngine
from shared.qdrant.client import QdrantManager


class RAGPipeline:
    """
    Main RAG pipeline for generating answers from knowledge bases.
    
    Flow:
    1. Retrieve relevant chunks from Qdrant (by chat_type_id)
    2. Rerank chunks by relevance
    3. Generate answer using LLM with retrieved context
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure models are loaded only once."""
        if cls._instance is None:
            cls._instance = super(RAGPipeline, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    @staticmethod
    def _load_prompt(prompt_name: str) -> str:
        """
        Load prompt template from markdown file.
        
        Args:
            prompt_name: Name of the prompt file (without .md extension)
            
        Returns:
            Prompt template as string
        """
        # Updated path to point to src/rag/prompts
        prompt_path = os.path.join(settings.BASE_DIR, "src", "rag", "prompts", f"{prompt_name}.md")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load prompt {prompt_name}: {e}")
            raise
    
    def __init__(self):
        if self._initialized:
            return
        
        logger.info("Initializing RAGPipeline...")
        
        # Provider cache: reuse Provider instances by (model, provider_alias)
        self._provider_cache: Dict[tuple, Provider] = {}
        self._provider_cache_lock = threading.Lock()
        
        # Initialize default LLM provider from settings (will be overridden per chat if needed)
        self.llm_provider = Provider(
            model_name=settings.LLM_MODEL,
            provider_alias=settings.LLM_PROVIDER
        )
        self._provider_cache[(settings.LLM_MODEL, settings.LLM_PROVIDER)] = self.llm_provider
        
        # Initialize Query Engine WITHOUT provider (will be set per request)
        self.query_engine = QueryEngine(primary_provider=None)
        
        # Initialize embedding engine based on config
        self.embedding_engine = self._create_embedding_engine()
        
        # Initialize Qdrant and retriever
        self.qdrant = QdrantManager()
        self.retriever = KnowledgeRetriever(self.qdrant, self.embedding_engine)
        
        # Load reranker model
        self.loader = ModelLoader()
        rerank_model, rerank_tokenizer = self.loader.load_reranker(settings.RERANKER_MODEL_ID)
        rerank_provider = HFRerankProvider(rerank_model, rerank_tokenizer)
        self.reranker = RerankerEngine(rerank_provider)
        
        self._initialized = True
        logger.info("RAGPipeline initialized successfully")
    
    def _create_embedding_engine(self) -> EmbeddingEngine:
        """
        Create embedding engine based on settings.EMBEDDING_PROVIDER.
        
        - "local": loads HuggingFace model locally (requires GPU/CPU resources)
        - "remote": uses OpenAI-compatible API (requires API key)
        
        Returns:
            Configured EmbeddingEngine instance
        """
        provider_type = settings.EMBEDDING_PROVIDER.lower()
        
        if provider_type == "remote":
            logger.info(f"Using remote embedding: model={settings.EMBEDDING_REMOTE_MODEL}, provider={settings.EMBEDDING_REMOTE_PROVIDER}")
            emb_provider = RemoteEmbeddingProvider(
                model_name=settings.EMBEDDING_REMOTE_MODEL,
                provider_alias=settings.EMBEDDING_REMOTE_PROVIDER
            )
        else:
            logger.info(f"Using local embedding: model={settings.EMBEDDING_MODEL_ID}")
            self.loader = ModelLoader()
            emb_model, emb_tokenizer = self.loader.load_embedding(settings.EMBEDDING_MODEL_ID)
            emb_provider = HFEmbeddingProvider(emb_model, emb_tokenizer)
        
        return EmbeddingEngine(emb_provider)
    
    def run(
        self,
        chat_type_id: UUID,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        k_retrieval: int = None,
        top_k: int = None,
        threshold: float = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute RAG pipeline for a query.
        
        Args:
            chat_type_id: ID of the ChatType to search in
            query: User's question
            chat_history: Optional chat history for context
            k_retrieval: Number of chunks to retrieve (default from settings)
            top_k: Number of chunks after reranking (default from settings)
            threshold: Minimum rerank score (default from settings)
            llm_model: Optional LLM model override (e.g., 'gpt-4', 'llama3.1:8b')
            llm_provider: Optional LLM provider override (ollama, openai, gemini)
            
        Returns:
            Dict with 'answer' and 'chunks' used
        """
        k_retrieval = k_retrieval or settings.K_RETRIEVAL
        top_k = top_k or settings.TOP_K
        threshold = threshold or settings.THRESHOLD
        
        logger.info(f"Processing query for chat_type_id={chat_type_id}: '{query[:50]}...' (model={llm_model}, provider={llm_provider})")
        
        try:
            # Get the LLM provider for this request (custom or default)
            request_provider = self._get_provider(llm_model, llm_provider)
            
            # Step 0: Contextualize Query (if history exists and has content)
            effective_query = query
            if chat_history and len(chat_history) > 0:
                effective_query = self.query_engine.contextualize_query(query, chat_history, provider=request_provider)
                logger.debug(f"Query contextualized: '{query}' -> '{effective_query}'")
            else:
                logger.debug("Skipping contextualization: no chat history available")

            # Step 1: Query Expansion (using custom model)
            expanded_queries = self.query_engine.expand_query(effective_query, provider=request_provider)
            query_texts = [q.text for q in expanded_queries]
            logger.info(f"Generated {len(query_texts)} search queries: {query_texts}")
            
            # Step 2: Retrieve relevant chunks (using multiple queries)
            raw_chunks = self.retriever.search_many(
                chat_type_id=chat_type_id,
                queries=query_texts,
                limit_per_query=k_retrieval
            )
            
            if not raw_chunks:
                logger.warning("No chunks retrieved")
                return {
                    "answer": "Desculpe, não encontrei informações relevantes na base de conhecimento para responder sua pergunta.",
                    "chunks": []
                }
            
            # Step 3: Rerank chunks
            reranked_chunks = self.reranker.rerank_chunks(
                query=query,
                chunks=raw_chunks,
                top_k=top_k,
                threshold=threshold
            )
            
            if not reranked_chunks:
                logger.warning("All chunks filtered out by reranker")
                return {
                    "answer": "Desculpe, as informações encontradas não eram relevantes o suficiente para responder sua pergunta com confiança.",
                    "chunks": []
                }
            
            logger.info(f"Selected {len(reranked_chunks)} chunks after reranking")
            
            # Step 4: Generate answer
            answer = self._generate_answer(query, reranked_chunks, chat_history, llm_model, llm_provider)
            
            return {
                "answer": answer,
                "chunks": reranked_chunks
            }
            
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            raise
    
    def run_stream(
        self,
        chat_type_id: UUID,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        k_retrieval: int = None,
        top_k: int = None,
        threshold: float = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None
    ):
        """
        Execute RAG pipeline with streaming response.
        Yields chunks of the generated answer.
        
        Args:
            chat_type_id: ID of the ChatType to search in
            query: User's question
            chat_history: Optional chat history for context
            k_retrieval: Number of chunks to retrieve (default from settings)
            top_k: Number of chunks after reranking (default from settings)
            threshold: Minimum rerank score (default from settings)
            llm_model: Optional LLM model override
            llm_provider: Optional LLM provider override
        """
        k_retrieval = k_retrieval or settings.K_RETRIEVAL
        top_k = top_k or settings.TOP_K
        threshold = threshold or settings.THRESHOLD
        
        logger.info(f"Processing streaming query for chat_type_id={chat_type_id} (model={llm_model}, provider={llm_provider})")
        
        try:
            # Get the LLM provider for this request (custom or default)
            request_provider = self._get_provider(llm_model, llm_provider)
            
            # Step 0: Contextualize Query (if history exists and has content)
            effective_query = query
            if chat_history and len(chat_history) > 0:
                effective_query = self.query_engine.contextualize_query(query, chat_history, provider=request_provider)
                logger.debug(f"Query contextualized: '{query}' -> '{effective_query}'")
            else:
                logger.debug("Skipping contextualization: no chat history available")

            # Step 1: Query Expansion (using custom model)
            expanded_queries = self.query_engine.expand_query(effective_query, provider=request_provider)
            query_texts = [q.text for q in expanded_queries]
            
            # Step 2: Retrieve
            raw_chunks = self.retriever.search_many(
                chat_type_id=chat_type_id,
                queries=query_texts,
                limit_per_query=k_retrieval
            )
            
            if not raw_chunks:
                yield {"type": "error", "content": "Desculpe, não encontrei informações relevantes na base de conhecimento."}
                return
            
            # Step 3: Rerank
            reranked_chunks = self.reranker.rerank_chunks(
                query=query,
                chunks=raw_chunks,
                top_k=top_k,
                threshold=threshold
            )
            
            if not reranked_chunks:
                yield {"type": "error", "content": "Desculpe, as informações encontradas não eram relevantes o suficiente."}
                return
            
            # Yield metadata (sources)
            formatted_sources = [
                {
                    "question": chunk["question"],
                    "answer": chunk["answer"],
                    "score": chunk.get("rerank_score", chunk.get("score", 0))
                }
                for chunk in reranked_chunks
            ]
            yield {"type": "sources", "content": formatted_sources}
            
            # Step 4: Generate Stream
            yield from self._generate_answer_stream(query, reranked_chunks, chat_history, llm_model, llm_provider)
            
        except Exception as e:
            logger.error(f"RAG pipeline stream failed: {e}")
            yield {"type": "error", "content": f"Erro no processamento: {str(e)}"}

    def _generate_answer_stream(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None
    ):
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Fonte {i}]\n"
                f"Pergunta: {chunk['question']}\n"
                f"Resposta: {chunk['answer']}"
            )
        
        context_str = "\n\n".join(context_parts)
        prompt_template = self._load_prompt("pipeline/message_system_prompt")
        system_prompt = prompt_template.format(context=context_str)
        
        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": query})
        
        try:
            # Use custom model if provided, otherwise use default
            provider = self._get_provider(llm_model, llm_provider)
            for token in provider.generate_stream(
                messages,
                temperature=0.3,
                max_new_tokens=1024
            ):
                yield {"type": "token", "content": token}
        except Exception as e:
            logger.error(f"Stream generation failed: {e}")
            yield {"type": "error", "content": "Erro ao gerar resposta."}

    def _generate_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None
    ) -> str:
        """
        Generate answer using LLM with retrieved context.
        
        Args:
            query: User's question
            chunks: Retrieved and reranked chunks
            chat_history: Optional chat history
            llm_model: Optional LLM model override
            llm_provider: Optional LLM provider override
            
        Returns:
            Generated answer
        """
        # Build context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Fonte {i}]\n"
                f"Pergunta: {chunk['question']}\n"
                f"Resposta: {chunk['answer']}"
            )
        
        context_str = "\n\n".join(context_parts)
        
        prompt_template = self._load_prompt("pipeline/message_system_prompt")
        system_prompt = prompt_template.format(context=context_str)
        
        messages = [{"role": "system", "content": system_prompt}]

        if chat_history:
            messages.extend(chat_history)
        
        messages.append({"role": "user", "content": query})
        
        try:
            logger.debug(f"Generating answer with {len(chunks)} chunks (model={llm_model}, provider={llm_provider})")
            provider = self._get_provider(llm_model, llm_provider)
            answer = provider.generate(
                messages, 
                temperature=0.3, 
                max_new_tokens=1024
            )
            return answer
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return "Desculpe, ocorreu um erro ao gerar a resposta. Por favor, tente novamente."
    
    def _get_provider(self, llm_model: Optional[str] = None, llm_provider: Optional[str] = None) -> Provider:
        """
        Get LLM provider instance, using custom model/provider if specified.
        Caches instances by (model, provider_alias) to reuse HTTP connection pools.
        
        Args:
            llm_model: Optional model name override
            llm_provider: Optional provider name override
            
        Returns:
            Provider instance configured with the specified or default model/provider
        """
        model = llm_model or settings.LLM_MODEL
        provider_alias = llm_provider or settings.LLM_PROVIDER
        cache_key = (model, provider_alias)
        
        with self._provider_cache_lock:
            if cache_key not in self._provider_cache:
                logger.debug(f"Creating new provider: model={model}, provider={provider_alias}")
                self._provider_cache[cache_key] = Provider(
                    model_name=model,
                    provider_alias=provider_alias
                )
            else:
                logger.debug(f"Reusing cached provider: model={model}, provider={provider_alias}")
        
        return self._provider_cache[cache_key]
