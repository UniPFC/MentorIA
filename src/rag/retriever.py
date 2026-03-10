"""
Knowledge retriever for semantic search in Qdrant.
"""

from typing import List, Dict, Any
from uuid import UUID
from config.logger import logger
from shared.qdrant.client import QdrantManager
from src.ai.embedding import EmbeddingEngine


class KnowledgeRetriever:
    """
    Retrieves relevant chunks from Qdrant using semantic search.
    """
    
    def __init__(self, qdrant_manager: QdrantManager, embedding_engine: EmbeddingEngine):
        """
        Initialize retriever.
        
        Args:
            qdrant_manager: QdrantManager instance
            embedding_engine: EmbeddingEngine for query embeddings
        """
        self.qdrant = qdrant_manager
        self.embedding_engine = embedding_engine
        logger.info("KnowledgeRetriever initialized")
    
    def search(
        self,
        chat_type_id: UUID,
        query: str,
        limit: int = 10,
        score_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks.
        
        Args:
            chat_type_id: ID of the ChatType
            query: Search query
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of chunk dicts with id, score, question, answer, metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_engine.embed_single(query)
            
            # Search in Qdrant
            results = self.qdrant.search(
                chat_type_id=chat_type_id,
                query_embedding=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            logger.debug(f"Retrieved {len(results)} chunks for chat_type_id={chat_type_id}")
            return results
            
        except Exception as e:
            logger.error(f"Search failed for chat_type_id={chat_type_id}: {e}")
            raise
    
    def search_many(
        self,
        chat_type_id: UUID,
        queries: List[str],
        limit_per_query: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search with multiple queries and deduplicate results.
        
        Args:
            chat_type_id: ID of the ChatType
            queries: List of search queries
            limit_per_query: Max results per query
            
        Returns:
            Deduplicated list of chunks
        """
        all_chunks = []
        seen_ids = set()
        
        for query in queries:
            chunks = self.search(chat_type_id, query, limit=limit_per_query)
            
            for chunk in chunks:
                if chunk['id'] not in seen_ids:
                    all_chunks.append(chunk)
                    seen_ids.add(chunk['id'])
        
        logger.debug(f"Retrieved {len(all_chunks)} unique chunks from {len(queries)} queries")
        return all_chunks
