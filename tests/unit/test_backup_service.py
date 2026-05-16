import os
import sys
import time
import tarfile
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.services import backup


@pytest.mark.unit
class TestBackupService:
    def test_get_backup_dir_creates_date_folder(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)

        backup_dir = backup.get_backup_dir(date_folder=True)

        assert os.path.isdir(backup_dir)
        assert backup_dir.startswith(str(tmp_path / 'cache' / 'backups'))
        assert len(Path(backup_dir).name) == 8

    def test_get_backup_dir_without_date_folder(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)

        backup_dir = backup.get_backup_dir(date_folder=False)

        assert os.path.isdir(backup_dir)
        assert backup_dir == str(tmp_path / 'cache' / 'backups')

    def test_backup_postgres_runs_pg_dump(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.POSTGRES_HOST = 'localhost'
        mock_settings.POSTGRES_PORT = 5432
        mock_settings.POSTGRES_USER = 'user'
        mock_settings.POSTGRES_DB = 'db'
        mock_settings.POSTGRES_PASSWORD = 'pass'
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'get_backup_dir', lambda date_folder=True: str(tmp_path))

        mock_run = MagicMock()
        monkeypatch.setattr(backup.subprocess, 'run', mock_run)

        dump_path = backup.backup_postgres()

        assert dump_path.endswith('.sql')
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == 'pg_dump'
        assert '-f' in cmd
        assert dump_path in cmd

    def test_backup_data_creates_tar_archive(self, tmp_path, monkeypatch):
        data_dir = tmp_path / 'data_dir'
        data_dir.mkdir()
        file_path = data_dir / 'file.txt'
        file_path.write_text('hello world')

        mock_settings = MagicMock()
        mock_settings.DATA_DIR = str(data_dir)
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'get_backup_dir', lambda date_folder=True: str(tmp_path))

        tar_path = backup.backup_data()

        assert tar_path.endswith('.tar.gz')
        assert os.path.exists(tar_path)

        with tarfile.open(tar_path, 'r:gz') as tar:
            names = tar.getnames()
            assert 'data/file.txt' in names

    def test_backup_qdrant_calls_snapshot_and_tars_storage(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.QDRANT_URL = 'http://localhost'
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'get_backup_dir', lambda date_folder=True: str(tmp_path))

        client = MagicMock()
        client.get_collections.return_value = SimpleNamespace(collections=[SimpleNamespace(name='test_collection')])
        client.create_snapshot.return_value = 'snapshot-id'

        fake_module = MagicMock()
        fake_module.QdrantClient.return_value = client
        monkeypatch.setitem(sys.modules, 'qdrant_client', fake_module)

        fake_tar = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_tar
        fake_context.__exit__.return_value = False
        monkeypatch.setattr(backup.tarfile, 'open', MagicMock(return_value=fake_context))

        qdrant_path = backup.backup_qdrant()

        assert qdrant_path.endswith('.tar.gz')
        client.get_collections.assert_called_once()
        client.create_snapshot.assert_called_once_with(collection_name='test_collection')
        fake_tar.add.assert_called_once_with('/qdrant/storage', arcname='qdrant_storage')

    def test_encrypt_and_decrypt_file_using_gpg_mock(self, tmp_path, monkeypatch):
        file_path = tmp_path / 'plain.txt'
        file_path.write_bytes(b'secret data')
        passphrase = 'testpass'

        gpg_instance = MagicMock()
        gpg_instance.encrypt_file.return_value = MagicMock(data=b'encrypted-bytes')
        gpg_instance.decrypt_file.return_value = MagicMock(ok=True, status='decrypted', data=b'restored-bytes')

        gpg_class = MagicMock(return_value=gpg_instance)
        monkeypatch.setattr(backup.gnupg, 'GPG', gpg_class)

        encrypted_path = backup.encrypt_file(str(file_path), passphrase)
        assert encrypted_path.endswith('.gpg')
        assert not file_path.exists()
        assert Path(encrypted_path).read_bytes() == b'encrypted-bytes'

        decrypted_path = backup.decrypt_file(encrypted_path, passphrase)
        assert decrypted_path.endswith('plain.txt')
        assert Path(decrypted_path).read_bytes() == b'restored-bytes'

    def test_decrypt_backups_processes_gpg_files(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)

        date_str = '01012026'
        backup_date_dir = tmp_path / 'cache' / 'backups' / date_str
        backup_date_dir.mkdir(parents=True)
        encrypted_file = backup_date_dir / 'file1.sql.gpg'
        encrypted_file.write_text('dummy')

        decrypted_dir = backup_date_dir / 'DECRYPTED'
        output_path = decrypted_dir / 'file1.sql'

        def fake_decrypt_file(src, passphrase, output_path_arg=None):
            return str(output_path)

        monkeypatch.setattr(backup, 'decrypt_file', fake_decrypt_file)

        results = backup.decrypt_backups(date_str=date_str, passphrase='secret')

        assert len(results) == 1
        assert str(output_path) in results

    def test_cleanup_old_backups_removes_old_date_folder(self, tmp_path, monkeypatch):
        base_dir = tmp_path / 'cache' / 'backups'
        base_dir.mkdir(parents=True)

        old_folder = base_dir / '01012026'
        old_folder.mkdir()
        recent_folder = base_dir / '02012026'
        recent_folder.mkdir()

        old_mtime = time.time() - (10 * 86400)
        recent_mtime = time.time()
        os.utime(old_folder, (old_mtime, old_mtime))
        os.utime(recent_folder, (recent_mtime, recent_mtime))

        backup.cleanup_old_backups(days=7, base_dir=str(base_dir))

        assert not old_folder.exists()
        assert recent_folder.exists()
