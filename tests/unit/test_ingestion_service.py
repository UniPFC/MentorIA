import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from io import BytesIO
import pandas as pd
from sqlalchemy.orm import Session
from src.services.ingestion import ChunkIngestionService
from shared.database.models.chat_type import ChatType


@pytest.mark.unit
class TestChunkIngestionService:
    @pytest.fixture
    def mock_embedding_engine(self):
        engine = MagicMock()
        engine.embed.return_value = [[0.1] * 384, [0.2] * 384]
        return engine
        
    @pytest.fixture
    def mock_qdrant_manager(self):
        manager = MagicMock()
        manager.insert_chunks.return_value = ["point_1", "point_2"]
        return manager
        
    @pytest.fixture
    def sample_excel_bytes(self):
        data = {
            "question": ["What is AI?", "What is ML?"],
            "answer": ["Artificial Intelligence", "Machine Learning"]
        }
        df = pd.DataFrame(data)
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        return buffer.getvalue()
        
    def test_init(self, mock_embedding_engine, mock_qdrant_manager):
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        
        assert service.embedding_engine == mock_embedding_engine
        assert service.qdrant_manager == mock_qdrant_manager
        
    def test_parse_spreadsheet_excel(self, mock_embedding_engine, mock_qdrant_manager, sample_excel_bytes):
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        
        chunks = service.parse_spreadsheet(sample_excel_bytes, "test.xlsx")
        
        assert len(chunks) == 2
        assert chunks[0]["question"] == "What is AI?"
        assert chunks[0]["answer"] == "Artificial Intelligence"
        assert chunks[0]["metadata"]["source_file"] == "test.xlsx"
        
    def test_parse_spreadsheet_csv(self, mock_embedding_engine, mock_qdrant_manager):
        data = {
            "question": ["Q1", "Q2"],
            "answer": ["A1", "A2"]
        }
        df = pd.DataFrame(data)
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        csv_bytes = buffer.getvalue()
        
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        chunks = service.parse_spreadsheet(csv_bytes, "test.csv")
        
        assert len(chunks) == 2

    def test_detect_csv_delimiter_comma(self, mock_embedding_engine, mock_qdrant_manager):
        csv_content = b"question,answer\nQ1,A1\nQ2,A2"
        
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        delimiter = service._detect_csv_delimiter(csv_content)
        
        assert delimiter == ','

    def test_detect_csv_delimiter_semicolon(self, mock_embedding_engine, mock_qdrant_manager):
        csv_content = b"question;answer\nQ1;A1\nQ2;A2"
        
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        delimiter = service._detect_csv_delimiter(csv_content)
        
        assert delimiter == ';'

    def test_parse_spreadsheet_csv_with_semicolon(self, mock_embedding_engine, mock_qdrant_manager):
        data = {
            "question": ["Q1", "Q2"],
            "answer": ["A1", "A2"]
        }
        df = pd.DataFrame(data)
        buffer = BytesIO()
        df.to_csv(buffer, index=False, sep=';')
        csv_bytes = buffer.getvalue()
        
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        chunks = service.parse_spreadsheet(csv_bytes, "test.csv")
        
        assert len(chunks) == 2
        assert chunks[0]["question"] == "Q1"
        assert chunks[0]["answer"] == "A1"

    def test_detect_encoding_utf8(self, mock_embedding_engine, mock_qdrant_manager):
        csv_content = "pergunta,resposta\nQ1,A1\nQ2,A2".encode('utf-8')
        
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        encoding = service._detect_encoding(csv_content)
        
        assert encoding == 'utf-8'

    def test_detect_encoding_latin1(self, mock_embedding_engine, mock_qdrant_manager):
        csv_content = "pergunta,resposta\nQ1,A1\nQ2,A2".encode('latin-1')
        
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        encoding = service._detect_encoding(csv_content)
        
        assert encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']

    def test_parse_spreadsheet_csv_with_latin1_encoding(self, mock_embedding_engine, mock_qdrant_manager):
        # Create CSV with Latin-1 encoding and special characters
        csv_content = "question,answer\nQual é a resposta?,Café\nOutra pergunta?,Açúcar".encode('latin-1')
        
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        chunks = service.parse_spreadsheet(csv_content, "test.csv")
        
        assert len(chunks) == 2
        assert "café" in chunks[0]["answer"].lower() or "açúcar" in chunks[1]["answer"].lower()
        
    def test_parse_spreadsheet_missing_columns(self, mock_embedding_engine, mock_qdrant_manager):
        data = {"col1": ["val1"], "col2": ["val2"]}
        df = pd.DataFrame(data)
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        
        with pytest.raises(ValueError, match="Required columns"):
            service.parse_spreadsheet(buffer.getvalue(), "test.xlsx")
            
    def test_parse_spreadsheet_unsupported_format(self, mock_embedding_engine, mock_qdrant_manager):
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            service.parse_spreadsheet(b"data", "test.txt")
            
    def test_ingest_chunks(self, mock_embedding_engine, mock_qdrant_manager, db_session: Session, sample_chat_type: ChatType):
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        
        chunks = [
            {"question": "Q1", "answer": "A1", "metadata": {"source_file": "test.xlsx"}},
            {"question": "Q2", "answer": "A2", "metadata": {"source_file": "test.xlsx"}}
        ]
        
        point_ids, total = service.ingest_chunks(sample_chat_type.id, chunks, db_session)
        
        assert len(point_ids) == 2
        assert total == 2
        mock_embedding_engine.embed.assert_called()
        mock_qdrant_manager.insert_chunks.assert_called_once()
        
    def test_ingest_chunks_empty(self, mock_embedding_engine, mock_qdrant_manager, db_session: Session, sample_chat_type: ChatType):
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        
        point_ids, total = service.ingest_chunks(sample_chat_type.id, [], db_session)
        
        assert len(point_ids) == 0
        assert total == 0
        
    def test_ingest_from_file(self, mock_embedding_engine, mock_qdrant_manager, db_session: Session, sample_chat_type: ChatType, sample_excel_bytes):
        service = ChunkIngestionService(mock_embedding_engine, mock_qdrant_manager)
        
        point_ids, total = service.ingest_from_file(
            chat_type_id=sample_chat_type.id,
            file_content=sample_excel_bytes,
            filename="test.xlsx",
            db_session=db_session
        )
        
        assert len(point_ids) == 2
        assert total == 2
        mock_embedding_engine.embed.assert_called()
        mock_qdrant_manager.insert_chunks.assert_called_once()
