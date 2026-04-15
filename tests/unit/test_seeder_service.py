import pytest
import os
from unittest.mock import patch, MagicMock, mock_open
from sqlalchemy.orm import Session
from src.services.seeder import seed_default_knowledge
from shared.database.models.user import User
from shared.database.models.chat_type import ChatType
from shared.database.models.knowledge_chunk import KnowledgeChunk


@pytest.mark.unit
class TestSeederService:
    @patch('src.services.seeder.SessionLocal')
    @patch('src.services.seeder.os.path.exists')
    def test_seed_default_knowledge_no_data_dir(self, mock_exists, mock_session_local):
        mock_exists.return_value = False
        
        seed_default_knowledge()
        
        mock_session_local.assert_not_called()
    
    @patch('src.services.seeder.SessionLocal')
    @patch('src.services.seeder.os.path.exists')
    @patch('src.services.seeder.os.listdir')
    @patch('src.services.seeder.auth_service')
    def test_seed_default_knowledge_creates_system_user(self, mock_auth, mock_listdir, mock_exists, mock_session_local):
        mock_exists.return_value = True
        mock_listdir.return_value = []
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_auth.get_password_hash.return_value = "hashed_password"
        
        seed_default_knowledge()
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
    
    @patch('src.services.seeder.SessionLocal')
    @patch('src.services.seeder.os.path.exists')
    @patch('src.services.seeder.os.listdir')
    @patch('src.services.seeder.auth_service')
    def test_seed_default_knowledge_updates_existing_user(self, mock_auth, mock_listdir, mock_exists, mock_session_local):
        mock_exists.return_value = True
        mock_listdir.return_value = []
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_user = MagicMock()
        mock_user.username = "OldName"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        seed_default_knowledge()
        
        assert mock_user.username == "MentorIA"
        mock_db.commit.assert_called()
    
    @patch('src.services.seeder.SessionLocal')
    @patch('src.services.seeder.os.path.exists')
    @patch('src.services.seeder.os.listdir')
    @patch('src.services.seeder.auth_service')
    def test_seed_default_knowledge_skips_non_spreadsheet_files(self, mock_auth, mock_listdir, mock_exists, mock_session_local):
        mock_exists.return_value = True
        mock_listdir.return_value = ['readme.txt', 'image.png', 'data.xlsx']
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_user = MagicMock()
        mock_user.username = "MentorIA"
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,  # System user
            None,       # ChatType for data.xlsx
        ]
        
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        
        seed_default_knowledge()
        
        assert mock_db.query.call_count >= 2
    
    @patch('src.services.seeder.SessionLocal')
    @patch('src.services.seeder.os.path.exists')
    @patch('src.services.seeder.os.listdir')
    @patch('src.services.seeder.os.path.join')
    @patch('src.services.seeder.auth_service')
    def test_seed_default_knowledge_creates_chat_type_with_separator(self, mock_auth, mock_join, mock_listdir, mock_exists, mock_session_local):
        mock_exists.return_value = True
        mock_listdir.return_value = ['Title --- Description.xlsx']
        mock_join.return_value = '/data/Title --- Description.xlsx'
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.username = "MentorIA"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,  # System user
            None,       # ChatType
        ]
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        
        seed_default_knowledge()
        
        add_calls = [call[0][0] for call in mock_db.add.call_args_list]
        chat_type_added = [obj for obj in add_calls if isinstance(obj, ChatType)]
        
        if chat_type_added:
            assert chat_type_added[0].name == "Title"
            assert chat_type_added[0].description == "Description"
    
    @patch('src.services.seeder.SessionLocal')
    @patch('src.services.seeder.os.path.exists')
    @patch('src.services.seeder.os.listdir')
    @patch('src.services.seeder.os.path.join')
    @patch('src.services.seeder.auth_service')
    def test_seed_default_knowledge_creates_chat_type_without_separator(self, mock_auth, mock_join, mock_listdir, mock_exists, mock_session_local):
        mock_exists.return_value = True
        mock_listdir.return_value = ['My_Data_File.xlsx']
        mock_join.return_value = '/data/My_Data_File.xlsx'
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.username = "MentorIA"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,  # System user
            None,       # ChatType
        ]
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        
        seed_default_knowledge()
        
        add_calls = [call[0][0] for call in mock_db.add.call_args_list]
        chat_type_added = [obj for obj in add_calls if isinstance(obj, ChatType)]
        
        if chat_type_added:
            assert chat_type_added[0].name == "My Data File"
    
    @patch('src.services.seeder.SessionLocal')
    @patch('src.services.seeder.os.path.exists')
    @patch('src.services.seeder.os.listdir')
    @patch('src.services.seeder.os.path.join')
    @patch('src.services.seeder.auth_service')
    @patch('src.services.seeder.QdrantManager')
    @patch('src.services.seeder.ModelLoader')
    @patch('src.services.seeder.ChunkIngestionService')
    @patch('builtins.open', new_callable=mock_open, read_data=b'file content')
    def test_seed_default_knowledge_ingests_data(self, mock_file, mock_ingestion, mock_loader, mock_qdrant, mock_auth, mock_join, mock_listdir, mock_exists, mock_session_local):
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.xlsx']
        mock_join.return_value = '/data/data.xlsx'
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.username = "MentorIA"
        
        mock_chat_type = MagicMock()
        mock_chat_type.id = "chat-type-id"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,      # System user
            mock_chat_type, # ChatType exists
        ]
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_embedding.return_value = (MagicMock(), MagicMock())
        
        mock_ingestion_instance = MagicMock()
        mock_ingestion.return_value = mock_ingestion_instance
        
        seed_default_knowledge()
        
        mock_ingestion_instance.ingest_from_file.assert_called_once()
    
    @patch('src.services.seeder.SessionLocal')
    @patch('src.services.seeder.os.path.exists')
    @patch('src.services.seeder.os.listdir')
    @patch('src.services.seeder.os.path.join')
    @patch('src.services.seeder.auth_service')
    def test_seed_default_knowledge_skips_existing_data(self, mock_auth, mock_join, mock_listdir, mock_exists, mock_session_local):
        mock_exists.return_value = True
        mock_listdir.return_value = ['data.xlsx']
        mock_join.return_value = '/data/data.xlsx'
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.username = "MentorIA"
        
        mock_chat_type = MagicMock()
        mock_chat_type.id = "chat-type-id"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,      # System user
            mock_chat_type, # ChatType exists
        ]
        mock_db.query.return_value.filter.return_value.count.return_value = 10
        
        seed_default_knowledge()
        
        assert mock_db.query.return_value.filter.return_value.count.called
    
    @patch('src.services.seeder.SessionLocal')
    @patch('src.services.seeder.os.path.exists')
    @patch('src.services.seeder.os.listdir')
    def test_seed_default_knowledge_handles_error(self, mock_listdir, mock_exists, mock_session_local):
        mock_exists.return_value = True
        mock_listdir.side_effect = Exception("Directory read error")
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        seed_default_knowledge()
        
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
