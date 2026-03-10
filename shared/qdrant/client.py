"""
Qdrant client wrapper for managing multiple collections (one per ChatType).

This module provides a high-level interface for:
- Creating collections dynamically based on chat_type_id
- Inserting chunks with embeddings
- Searching for relevant chunks by collection
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from config.settings import settings
from config.logger import logger
import uuid
from uuid import UUID


class QdrantManager:
    """
    Manages Qdrant collections for the RAG chat system.
    Each ChatType has its own collection for isolated knowledge bases.
    """
    
    def __init__(self):
        """Initialize Qdrant client connection."""
        try:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                timeout=30.0
            )
            logger.info(f"Connected to Qdrant at {settings.QDRANT_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    def get_collection_name(self, chat_type_id: UUID) -> str:
        """Generate collection name for a chat type."""
        return f"chat_type_{chat_type_id}"
    
    def create_collection(
        self, 
        chat_type_id: UUID, 
        vector_size: int = 1024,
        distance: Distance = Distance.COSINE
    ) -> bool:
        """
        Create a new collection for a ChatType.
        
        Args:
            chat_type_id: ID of the ChatType
            vector_size: Dimension of embedding vectors (default: 1024 for mxbai-embed-large-v1)
            distance: Distance metric for similarity search
            
        Returns:
            bool: True if created successfully or already exists
        """
        collection_name = self.get_collection_name(chat_type_id)
        
        try:
            # Check if collection already exists
            collections = self.client.get_collections().collections
            if any(col.name == collection_name for col in collections):
                logger.info(f"Collection '{collection_name}' already exists.")
                return True
            
            # Create new collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            logger.info(f"Created collection '{collection_name}' with vector_size={vector_size}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            raise
    
    def delete_collection(self, chat_type_id: UUID) -> bool:
        """
        Delete a collection for a ChatType.
        
        Args:
            chat_type_id: ID of the ChatType
            
        Returns:
            bool: True if deleted successfully
        """
        collection_name = self.get_collection_name(chat_type_id)
        
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {e}")
            return False
    
    def insert_chunks(
        self,
        chat_type_id: UUID,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> List[str]:
        """
        Insert chunks with embeddings into a collection.
        
        Args:
            chat_type_id: ID of the ChatType
            chunks: List of chunk dictionaries with keys: question, answer, metadata
            embeddings: List of embedding vectors (same length as chunks)
            
        Returns:
            List[str]: List of generated point IDs
        """
        collection_name = self.get_collection_name(chat_type_id)
        
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks count ({len(chunks)}) must match embeddings count ({len(embeddings)})")
        
        try:
            points = []
            point_ids = []
            
            for chunk, embedding in zip(chunks, embeddings):
                point_id = str(uuid.uuid4())
                point_ids.append(point_id)
                
                payload = {
                    "question": chunk.get("question", ""),
                    "answer": chunk.get("answer", ""),
                    "metadata": chunk.get("metadata", {})
                }
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                )
            
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            logger.info(f"Inserted {len(points)} chunks into collection '{collection_name}'")
            return point_ids
            
        except Exception as e:
            logger.error(f"Failed to insert chunks into '{collection_name}': {e}")
            raise
    
    def search(
        self,
        chat_type_id: UUID,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks in a collection.
        
        Args:
            chat_type_id: ID of the ChatType
            query_embedding: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (optional)
            
        Returns:
            List of dicts with keys: id, score, question, answer, metadata
        """
        collection_name = self.get_collection_name(chat_type_id)
        
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            chunks = []
            for result in results:
                chunks.append({
                    "id": result.id,
                    "score": result.score,
                    "question": result.payload.get("question", ""),
                    "answer": result.payload.get("answer", ""),
                    "metadata": result.payload.get("metadata", {})
                })
            
            logger.info(f"Found {len(chunks)} chunks in collection '{collection_name}'")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to search in collection '{collection_name}': {e}")
            raise
    
    def get_collection_info(self, chat_type_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get information about a collection.
        
        Args:
            chat_type_id: ID of the ChatType
            
        Returns:
            Dict with collection info or None if not found
        """
        collection_name = self.get_collection_name(chat_type_id)
        
        try:
            info = self.client.get_collection(collection_name=collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.warning(f"Collection '{collection_name}' not found: {e}")
            return None
