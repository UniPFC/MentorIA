import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from src.api.routes import admin
from src.api.routes.admin import (
    verify_admin_slug,
    verify_admin_user,
    verify_slug,
    trigger_backup,
    list_backups,
    restore_backup,
    delete_backup,
    RestoreRequest
)


@pytest.mark.unit
class TestAdminRoutes:
    """Testes unitários para rotas de administração"""

    def test_verify_admin_slug_success(self, monkeypatch):
        """Testa verificação de admin slug com sucesso"""
        mock_settings = MagicMock()
        mock_settings.ADMIN_SLUG = "correct-slug"
        monkeypatch.setattr(admin, "settings", mock_settings)

        assert verify_admin_slug("correct-slug") is True

    def test_verify_admin_slug_failure(self, monkeypatch):
        """Testa verificação de admin slug com falha (403)"""
        mock_settings = MagicMock()
        mock_settings.ADMIN_SLUG = "correct-slug"
        monkeypatch.setattr(admin, "settings", mock_settings)

        with pytest.raises(HTTPException) as exc_info:
            verify_admin_slug("wrong-slug")
        
        assert exc_info.value.status_code == 403
        assert "not authorized" in exc_info.value.detail

    def test_verify_admin_user_success(self, monkeypatch):
        """Testa verificação de usuário administrador do sistema"""
        mock_settings = MagicMock()
        mock_settings.SYSTEM_USER_EMAIL = "admin@system.com"
        monkeypatch.setattr(admin, "settings", mock_settings)

        user = Mock()
        user.email = "admin@system.com"

        assert verify_admin_user(user) == user

    def test_verify_admin_user_failure(self, monkeypatch):
        """Testa verificação de usuário administrador do sistema com email diferente (403)"""
        mock_settings = MagicMock()
        mock_settings.SYSTEM_USER_EMAIL = "admin@system.com"
        monkeypatch.setattr(admin, "settings", mock_settings)

        user = Mock()
        user.email = "normal_user@system.com"

        with pytest.raises(HTTPException) as exc_info:
            verify_admin_user(user)
        
        assert exc_info.value.status_code == 403
        assert "not authorized" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_slug_endpoint(self):
        """Testa o endpoint de verificação do slug"""
        result = await verify_slug("any-slug", True)
        assert result == {"success": True, "message": "Slug verified"}

    @pytest.mark.asyncio
    async def test_trigger_backup_success(self, monkeypatch):
        """Testa o trigger_backup endpoint com sucesso total (incluindo qdrant)"""
        monkeypatch.setenv("BACKUP_PASSPHRASE", "secret_pass")
        
        backup_postgres_mock = Mock(return_value="db_dump.sql")
        backup_data_mock = Mock(return_value="data_dump.tar.gz")
        backup_qdrant_mock = Mock(return_value="qdrant_dump.tar.gz")
        encrypt_file_mock = Mock(side_effect=lambda x, y: x + ".gpg")
        cleanup_mock = Mock()

        monkeypatch.setattr(admin, "backup_postgres", backup_postgres_mock)
        monkeypatch.setattr(admin, "backup_data", backup_data_mock)
        monkeypatch.setattr(admin, "backup_qdrant", backup_qdrant_mock)
        monkeypatch.setattr(admin, "encrypt_file", encrypt_file_mock)
        monkeypatch.setattr(admin, "cleanup_old_backups", cleanup_mock)

        current_user = Mock()
        
        response = await trigger_backup("slug", True, current_user)
        
        assert response.success is True
        assert "completed successfully" in response.message
        assert response.files == ["db_dump.sql.gpg", "data_dump.tar.gz.gpg", "qdrant_dump.tar.gz.gpg"]
        backup_postgres_mock.assert_called_once()
        backup_data_mock.assert_called_once()
        backup_qdrant_mock.assert_called_once()
        cleanup_mock.assert_called_once_with(days=7)

    @pytest.mark.asyncio
    async def test_trigger_backup_qdrant_error_ignored(self, monkeypatch):
        """Testa o trigger_backup endpoint ignorando erros ao fazer backup do Qdrant"""
        monkeypatch.setenv("BACKUP_PASSPHRASE", "secret_pass")
        
        backup_postgres_mock = Mock(return_value="db_dump.sql")
        backup_data_mock = Mock(return_value="data_dump.tar.gz")
        backup_qdrant_mock = Mock(side_effect=Exception("Qdrant connection failed"))
        encrypt_file_mock = Mock(side_effect=lambda x, y: x + ".gpg")
        cleanup_mock = Mock()

        monkeypatch.setattr(admin, "backup_postgres", backup_postgres_mock)
        monkeypatch.setattr(admin, "backup_data", backup_data_mock)
        monkeypatch.setattr(admin, "backup_qdrant", backup_qdrant_mock)
        monkeypatch.setattr(admin, "encrypt_file", encrypt_file_mock)
        monkeypatch.setattr(admin, "cleanup_old_backups", cleanup_mock)

        current_user = Mock()
        
        response = await trigger_backup("slug", True, current_user)
        
        assert response.success is True
        # response files should only contain postgres and data backups since qdrant failed
        assert response.files == ["db_dump.sql.gpg", "data_dump.tar.gz.gpg"]
        backup_postgres_mock.assert_called_once()
        backup_data_mock.assert_called_once()
        backup_qdrant_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_backup_missing_passphrase(self, monkeypatch):
        """Testa o trigger_backup endpoint quando a passphrase de backup não está definida (500)"""
        monkeypatch.delenv("BACKUP_PASSPHRASE", raising=False)
        current_user = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await trigger_backup("slug", True, current_user)
        
        assert exc_info.value.status_code == 500
        assert "BACKUP_PASSPHRASE not set" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_trigger_backup_failure_exception(self, monkeypatch):
        """Testa trigger_backup lidando com exceções gerais (500)"""
        monkeypatch.setenv("BACKUP_PASSPHRASE", "secret_pass")
        
        backup_postgres_mock = Mock(side_effect=Exception("Database connection timed out"))
        monkeypatch.setattr(admin, "backup_postgres", backup_postgres_mock)

        current_user = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await trigger_backup("slug", True, current_user)
        
        assert exc_info.value.status_code == 500
        assert "Backup failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_backups_success(self, monkeypatch, tmp_path):
        """Testa listagem de backups com sucesso"""
        # Mock get_backup_dir to return base directory
        base_dir = tmp_path / "cache" / "backups"
        base_dir.mkdir(parents=True)
        
        # Create some fake backup folders
        folder_valid = base_dir / "01012026"
        folder_valid.mkdir()
        # Create a file inside valid folder
        file1 = folder_valid / "postgres_backup.sql.gpg"
        file1.write_text("encrypted content")
        
        folder_invalid_name = base_dir / "not-digits"
        folder_invalid_name.mkdir()
        
        file_at_root = base_dir / "ignored_file.txt"
        file_at_root.write_text("ignored")

        get_backup_dir_mock = Mock(return_value=str(base_dir))
        monkeypatch.setattr(admin, "get_backup_dir", get_backup_dir_mock)

        current_user = Mock()
        response = await list_backups("slug", True, current_user)
        
        get_backup_dir_mock.assert_called_once_with(date_folder=False)
        assert "01012026" in response.date_folders
        assert "not-digits" not in response.date_folders
        assert "01012026" in response.current_backups
        
        backup_files = response.current_backups["01012026"]
        assert len(backup_files) == 1
        assert backup_files[0]["name"] == "postgres_backup.sql.gpg"
        assert backup_files[0]["size"] == file1.stat().st_size

    @pytest.mark.asyncio
    async def test_list_backups_empty_dir_not_exists(self, monkeypatch, tmp_path):
        """Testa listagem de backups quando o diretório base não existe"""
        non_existent_dir = str(tmp_path / "non_existent_backups_folder")
        get_backup_dir_mock = Mock(return_value=non_existent_dir)
        monkeypatch.setattr(admin, "get_backup_dir", get_backup_dir_mock)

        current_user = Mock()
        response = await list_backups("slug", True, current_user)
        
        assert response.date_folders == []
        assert response.current_backups == {}

    @pytest.mark.asyncio
    async def test_list_backups_exception(self, monkeypatch):
        """Testa falha de listagem de backups lidando com exceção (500)"""
        get_backup_dir_mock = Mock(side_effect=Exception("Disk read error"))
        monkeypatch.setattr(admin, "get_backup_dir", get_backup_dir_mock)

        current_user = Mock()
        with pytest.raises(HTTPException) as exc_info:
            await list_backups("slug", True, current_user)
        
        assert exc_info.value.status_code == 500
        assert "Failed to list backups" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_restore_backup_success(self, monkeypatch):
        """Testa restauração de backup com sucesso"""
        # Mock engine dispose
        engine_mock = MagicMock()
        monkeypatch.setattr("shared.database.session.engine", engine_mock)

        restore_backups_mock = Mock()
        monkeypatch.setattr(admin, "restore_backups", restore_backups_mock)

        current_user = Mock()
        request = RestoreRequest(date_str="01012026", passphrase="custom-pass")
        
        response = await restore_backup("slug", request, True, current_user)
        
        assert response.success is True
        assert "restored successfully" in response.message
        assert "01/01/2026" in response.message
        engine_mock.dispose.assert_called_once()
        restore_backups_mock.assert_called_once_with(date_str="01012026", passphrase="custom-pass")

    @pytest.mark.asyncio
    async def test_restore_backup_missing_passphrase(self, monkeypatch):
        """Testa restauração de backup sem passphrase na request e no ambiente (500)"""
        monkeypatch.delenv("BACKUP_PASSPHRASE", raising=False)
        current_user = Mock()
        request = RestoreRequest(date_str="01012026", passphrase=None)

        with pytest.raises(HTTPException) as exc_info:
            await restore_backup("slug", request, True, current_user)
        
        assert exc_info.value.status_code == 500
        assert "BACKUP_PASSPHRASE not set" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_restore_backup_not_found(self, monkeypatch):
        """Testa restauração de backup com data inexistente (404)"""
        monkeypatch.setenv("BACKUP_PASSPHRASE", "secret_pass")
        engine_mock = MagicMock()
        monkeypatch.setattr("shared.database.session.engine", engine_mock)

        restore_backups_mock = Mock(side_effect=FileNotFoundError("Backup folder not found"))
        monkeypatch.setattr(admin, "restore_backups", restore_backups_mock)

        current_user = Mock()
        request = RestoreRequest(date_str="01012026")

        with pytest.raises(HTTPException) as exc_info:
            await restore_backup("slug", request, True, current_user)
        
        assert exc_info.value.status_code == 404
        assert "Backup folder not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_restore_backup_failure_exception(self, monkeypatch):
        """Testa restauração de backup lidando com exceção genérica (500)"""
        monkeypatch.setenv("BACKUP_PASSPHRASE", "secret_pass")
        engine_mock = MagicMock()
        monkeypatch.setattr("shared.database.session.engine", engine_mock)

        restore_backups_mock = Mock(side_effect=Exception("Decryption error"))
        monkeypatch.setattr(admin, "restore_backups", restore_backups_mock)

        current_user = Mock()
        request = RestoreRequest(date_str="01012026")

        with pytest.raises(HTTPException) as exc_info:
            await restore_backup("slug", request, True, current_user)
        
        assert exc_info.value.status_code == 500
        assert "Restore failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_backup_success(self, monkeypatch, tmp_path):
        """Testa deleção de pasta de backup com sucesso"""
        base_dir = tmp_path / "cache" / "backups"
        base_dir.mkdir(parents=True)
        date_folder = base_dir / "01012026"
        date_folder.mkdir()

        get_backup_dir_mock = Mock(return_value=str(base_dir))
        monkeypatch.setattr(admin, "get_backup_dir", get_backup_dir_mock)

        current_user = Mock()
        response = await delete_backup("slug", "01012026", True, current_user)
        
        assert response.success is True
        assert "deleted successfully" in response.message
        assert not date_folder.exists()

    @pytest.mark.asyncio
    async def test_delete_backup_not_found(self, monkeypatch, tmp_path):
        """Testa deleção de pasta de backup que não existe (404)"""
        base_dir = tmp_path / "cache" / "backups"
        base_dir.mkdir(parents=True)

        get_backup_dir_mock = Mock(return_value=str(base_dir))
        monkeypatch.setattr(admin, "get_backup_dir", get_backup_dir_mock)

        current_user = Mock()
        with pytest.raises(HTTPException) as exc_info:
            await delete_backup("slug", "01012026", True, current_user)
        
        assert exc_info.value.status_code == 404
        assert "Backup folder not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_backup_failure_exception(self, monkeypatch):
        """Testa falha de deleção de backup lidando com exceção genérica (500)"""
        get_backup_dir_mock = Mock(side_effect=Exception("Permission denied"))
        monkeypatch.setattr(admin, "get_backup_dir", get_backup_dir_mock)

        current_user = Mock()
        with pytest.raises(HTTPException) as exc_info:
            await delete_backup("slug", "01012026", True, current_user)
        
        assert exc_info.value.status_code == 500
        assert "Failed to delete backup" in exc_info.value.detail
