"""
Chunk ingestion service for processing spreadsheets and storing in Qdrant.
Handles: Excel/CSV upload → parsing → embedding → Qdrant storage.
"""

import json
from typing import List, Dict, Any, Tuple
import pandas as pd
from uuid import UUID
from io import BytesIO, StringIO
from config.logger import logger
from shared.qdrant.client import QdrantManager
from shared.database.models.knowledge_chunk import KnowledgeChunk
from src.ai.embedding import EmbeddingEngine


class ChunkIngestionService:
    """
    Service for ingesting question-answer chunks into Qdrant.
    """
    
    def __init__(self, embedding_engine: EmbeddingEngine, qdrant_manager: QdrantManager):
        """
        Initialize ingestion service.
        
        Args:
            embedding_engine: EmbeddingEngine for generating embeddings
            qdrant_manager: QdrantManager for vector storage
        """
        self.embedding_engine = embedding_engine
        self.qdrant_manager = qdrant_manager
        logger.info("ChunkIngestionService initialized")
    
    def _detect_encoding(self, file_content: bytes) -> str:
        """
        Detect file encoding by trying common encodings.
        
        Args:
            file_content: File bytes
            
        Returns:
            Detected encoding (utf-8, latin-1, cp1252, etc.)
        """
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16']
        
        for encoding in encodings:
            try:
                file_content.decode(encoding)
                logger.debug(f"Detected encoding: {encoding}")
                return encoding
            except (UnicodeDecodeError, LookupError):
                continue
        
        logger.warning("Could not detect encoding, defaulting to latin-1")
        return 'latin-1'

    def _detect_csv_delimiter(self, file_content: bytes) -> str:
        """
        Detect CSV delimiter (comma or semicolon) by analyzing first line.
        
        Args:
            file_content: File bytes
            
        Returns:
            Detected delimiter (',' or ';')
        """
        try:
            # Detect encoding first
            encoding = self._detect_encoding(file_content)
            text_content = file_content.decode(encoding, errors='ignore')
            first_line = text_content.split('\n')[0]
            
            # Count occurrences of common delimiters
            comma_count = first_line.count(',')
            semicolon_count = first_line.count(';')
            
            # Return the most frequent delimiter, default to comma
            if semicolon_count > comma_count:
                logger.debug(f"Detected CSV delimiter: semicolon (;)")
                return ';'
            else:
                logger.debug(f"Detected CSV delimiter: comma (,)")
                return ','
        except Exception as e:
            logger.warning(f"Failed to detect CSV delimiter, defaulting to comma: {e}")
            return ','

    def parse_spreadsheet(
        self, 
        file_content: bytes, 
        filename: str,
        question_col: str = "question",
        answer_col: str = "answer"
    ) -> List[Dict[str, Any]]:
        """
        Parse spreadsheet file into chunks.
        
        Args:
            file_content: File bytes
            filename: Original filename
            question_col: Column name for questions
            answer_col: Column name for answers
            
        Returns:
            List of chunk dicts with question, answer, metadata
        """
        try:
            # Detect file type and read
            if filename.endswith('.csv'):
                delimiter = self._detect_csv_delimiter(file_content)
                encoding = self._detect_encoding(file_content)
                df = pd.read_csv(BytesIO(file_content), delimiter=delimiter, encoding=encoding)
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(BytesIO(file_content))
            else:
                raise ValueError(f"Unsupported file format: {filename}")
            
            # Validate columns
            if question_col not in df.columns or answer_col not in df.columns:
                raise ValueError(f"Required columns '{question_col}' and '{answer_col}' not found in file")
            
            # Parse chunks
            chunks = []
            for idx, row in df.iterrows():
                question = str(row[question_col]).strip()
                answer = str(row[answer_col]).strip()
                
                if question and answer and question != 'nan' and answer != 'nan':
                    chunks.append({
                        "question": question,
                        "answer": answer,
                        "metadata": {
                            "source_file": filename,
                            "row_number": int(idx) + 2  # +2 for header and 0-indexing
                        }
                    })
            
            logger.info(f"Parsed {len(chunks)} chunks from {filename}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to parse spreadsheet {filename}: {e}")
            raise
    
    def ingest_chunks(
        self,
        chat_type_id: UUID,
        chunks: List[Dict[str, Any]],
        db_session: Any,
        batch_size: int = 32,
        on_progress: callable = None
    ) -> Tuple[List[str], int]:
        """
        Ingest chunks into Qdrant with embeddings.
        
        Args:
            chat_type_id: ID of the ChatType
            chunks: List of chunk dicts
            db_session: Database session for saving metadata
            batch_size: Batch size for embedding generation
            on_progress: Optional callback function(processed_count) for progress tracking
            
        Returns:
            Tuple of (point_ids, total_ingested)
        """
        if not chunks:
            logger.warning("No chunks to ingest")
            return [], 0
        
        try:
            # Prepare texts for embedding (question + answer concatenated)
            texts = [f"{chunk['question']}\n\n{chunk['answer']}" for chunk in chunks]
            
            # Generate embeddings in batches
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = self.embedding_engine.embed(batch_texts)
                all_embeddings.extend(batch_embeddings)
                logger.debug(f"Generated embeddings for batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
            
            # Insert into Qdrant
            point_ids = self.qdrant_manager.insert_chunks(
                chat_type_id=chat_type_id,
                chunks=chunks,
                embeddings=all_embeddings
            )
            
            # Save metadata to database with progress tracking
            for i, point_id in enumerate(point_ids):
                chunk_data = chunks[i]
                metadata = chunk_data.get("metadata", {})
                
                knowledge_chunk = KnowledgeChunk(
                    chat_type_id=chat_type_id,
                    qdrant_point_id=point_id,
                    source_file=metadata.get("source_file"),
                    row_number=metadata.get("row_number"),
                    chunk_metadata=json.dumps(metadata)
                )
                db_session.add(knowledge_chunk)
                
                # Update progress every batch_size chunks or at the end
                if (i + 1) % batch_size == 0 or (i + 1) == len(point_ids):
                    db_session.commit()
                    if on_progress:
                        try:
                            on_progress(i + 1)
                        except Exception as e:
                            logger.warning(f"Progress callback failed: {e}")
            
            # Final commit if not already done
            db_session.commit()
            
            logger.info(f"Successfully ingested {len(point_ids)} chunks for chat_type_id={chat_type_id}")
            return point_ids, len(point_ids)
            
        except Exception as e:
            logger.error(f"Failed to ingest chunks for chat_type_id={chat_type_id}: {e}")
            raise
    
    def ingest_from_file(
        self,
        chat_type_id: UUID,
        file_content: bytes,
        filename: str,
        db_session: Any,
        question_col: str = "question",
        answer_col: str = "answer"
    ) -> Tuple[List[str], int]:
        """
        Complete ingestion pipeline: parse file → embed → store.
        
        Args:
            chat_type_id: ID of the ChatType
            file_content: File bytes
            filename: Original filename
            db_session: Database session
            question_col: Column name for questions
            answer_col: Column name for answers
            
        Returns:
            Tuple of (point_ids, total_ingested)
        """
        logger.info(f"Starting ingestion pipeline for chat_type_id={chat_type_id}, file={filename}")
        
        # Parse spreadsheet
        chunks = self.parse_spreadsheet(file_content, filename, question_col, answer_col)
        
        # Ingest chunks
        point_ids, total = self.ingest_chunks(chat_type_id, chunks, db_session)
        
        logger.info(f"Ingestion pipeline completed: {total} chunks ingested")
        return point_ids, total
