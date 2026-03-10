"""
RAG Pipeline for multi-tenant chat system.
Adapted from SoulsborneRAG to work with dynamic chat_type_id.
"""

import os
from typing import List, Dict, Any, Optional
from uuid import UUID
from config.logger import logger
from config.settings import settings
from src.rag.retriever import KnowledgeRetriever
from src.rag.reranker import RerankerEngine
from src.ai.provider.llm import Provider
from src.ai.loader import ModelLoader
from src.ai.provider.embedding import HFEmbeddingProvider
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
        prompt_path = os.path.join(settings.BASE_DIR, "prompts", f"{prompt_name}.md")
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
        
        # Initialize LLM provider from settings
        self.llm_provider = Provider(
            model_name=settings.LLM_MODEL,
            provider_alias=settings.LLM_PROVIDER
        )
        
        # Initialize model loader
        self.loader = ModelLoader()
        
        # Load embedding model
        emb_model, emb_tokenizer = self.loader.load_embedding(settings.EMBEDDING_MODEL_ID)
        emb_provider = HFEmbeddingProvider(emb_model, emb_tokenizer)
        self.embedding_engine = EmbeddingEngine(emb_provider)
        
        # Initialize Qdrant and retriever
        self.qdrant = QdrantManager()
        self.retriever = KnowledgeRetriever(self.qdrant, self.embedding_engine)
        
        # Load reranker model
        rerank_model, rerank_tokenizer = self.loader.load_reranker(settings.RERANKER_MODEL_ID)
        rerank_provider = HFRerankProvider(rerank_model, rerank_tokenizer)
        self.reranker = RerankerEngine(rerank_provider)
        
        self._initialized = True
        logger.info("RAGPipeline initialized successfully")
    
    def run(
        self,
        chat_type_id: UUID,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        k_retrieval: int = None,
        top_k: int = None,
        threshold: float = None
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
            
        Returns:
            Dict with 'answer' and 'chunks' used
        """
        k_retrieval = k_retrieval or settings.K_RETRIEVAL
        top_k = top_k or settings.TOP_K
        threshold = threshold or settings.THRESHOLD
        
        logger.info(f"Processing query for chat_type_id={chat_type_id}: '{query[:50]}...'")
        
        try:
            # Step 1: Retrieve relevant chunks
            raw_chunks = self.retriever.search(
                chat_type_id=chat_type_id,
                query=query,
                limit=k_retrieval
            )
            
            if not raw_chunks:
                logger.warning("No chunks retrieved")
                return {
                    "answer": "Desculpe, não encontrei informações relevantes na base de conhecimento para responder sua pergunta.",
                    "chunks": []
                }
            
            # Step 2: Rerank chunks
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
            
            # Step 3: Generate answer
            answer = self._generate_answer(query, reranked_chunks, chat_history)
            
            return {
                "answer": answer,
                "chunks": reranked_chunks
            }
            
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            raise
    
    def _generate_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate answer using LLM with retrieved context.
        
        Args:
            query: User's question
            chunks: Retrieved and reranked chunks
            chat_history: Optional chat history
            
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
        
        # Load system prompt template and format with context
        prompt_template = self._load_prompt("rag_system")
        system_prompt = prompt_template.format(context=context_str)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history if provided
        if chat_history:
            messages.extend(chat_history)
        
        # Add current query
        messages.append({"role": "user", "content": query})
        
        # Generate answer
        try:
            logger.debug(f"Generating answer with {len(chunks)} chunks")
            answer = self.llm_provider.generate(messages, temperature=0.3, max_new_tokens=512)
            return answer
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return "Desculpe, ocorreu um erro ao gerar a resposta. Por favor, tente novamente."
