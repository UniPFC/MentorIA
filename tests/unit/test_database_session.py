import pytest
from unittest.mock import patch, MagicMock
from shared.database.session import get_db, SessionLocal


@pytest.mark.unit
class TestDatabaseSession:
    @patch('shared.database.session.SessionLocal')
    def test_get_db_yields_session(self, mock_session_local):
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        gen = get_db()
        db = next(gen)
        
        assert db == mock_session
        mock_session_local.assert_called_once()
    
    @patch('shared.database.session.SessionLocal')
    def test_get_db_closes_session(self, mock_session_local):
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        gen = get_db()
        next(gen)
        
        try:
            next(gen)
        except StopIteration:
            pass
        
        mock_session.close.assert_called_once()
    
    @patch('shared.database.session.SessionLocal')
    def test_get_db_closes_on_exception(self, mock_session_local):
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        gen = get_db()
        next(gen)
        
        try:
            gen.throw(Exception("Test error"))
        except Exception:
            pass
        
        mock_session.close.assert_called_once()
