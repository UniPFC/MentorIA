import datetime
import io
import os
import shutil
import sys
import tarfile
import time
from pathlib import Path
from types import SimpleNamespace
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
        mock_settings.QDRANT_STORAGE_DIR = str(tmp_path / 'qdrant_storage')
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'get_backup_dir', lambda date_folder=True: str(tmp_path))

        (tmp_path / 'qdrant_storage').mkdir()
        # Create a test file in the storage directory to simulate items
        (tmp_path / 'qdrant_storage' / 'test_file.txt').write_text('test')

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
        # The implementation adds each item in the storage directory individually
        assert fake_tar.add.called

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

    def test_restore_postgres_in_memory_calls_psql(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.POSTGRES_HOST = 'localhost'
        mock_settings.POSTGRES_PORT = 5432
        mock_settings.POSTGRES_USER = 'user'
        mock_settings.POSTGRES_DB = 'db'
        mock_settings.POSTGRES_PASSWORD = 'pass'
        monkeypatch.setattr(backup, 'settings', mock_settings)

        encrypted_path = tmp_path / 'backup.sql.gpg'
        encrypted_path.write_text('encrypted')

        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.return_value = MagicMock(ok=True, status='decrypted', data=b'SELECT 1;')
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b'', b'')
        monkeypatch.setattr(backup.subprocess, 'Popen', MagicMock(return_value=process_mock))

        backup.restore_postgres_in_memory(str(encrypted_path), 'passphrase')

        # The implementation calls Popen twice: once for drop/recreate, once for restore
        assert backup.subprocess.Popen.call_count == 2
        assert process_mock.communicate.called

    def test_restore_tar_in_memory_extracts_files(self, tmp_path, monkeypatch):
        encrypted_path = tmp_path / 'backup.tar.gz.gpg'
        encrypted_path.write_text('encrypted')

        tar_bytes = io.BytesIO()
        with tarfile.open(fileobj=tar_bytes, mode='w:gz') as tar:
            content = tmp_path / 'hello.txt'
            content.write_text('hello')
            tar.add(str(content), arcname='hello.txt')
        tar_bytes.seek(0)

        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.return_value = MagicMock(ok=True, status='decrypted', data=tar_bytes.getvalue())
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        extract_path = tmp_path / 'extract'
        backup.restore_tar_in_memory(str(encrypted_path), 'passphrase', str(extract_path))

        assert (extract_path / 'hello.txt').read_text() == 'hello'

    def test_wait_for_postgres_ready_returns_when_connected(self, monkeypatch):
        conn_mock = MagicMock()
        monkeypatch.setattr(backup.psycopg2, 'connect', MagicMock(return_value=conn_mock))

        backup.wait_for_postgres_ready()

        backup.psycopg2.connect.assert_called_once()

    def test_wait_for_qdrant_ready_returns_on_http_200(self, monkeypatch):
        mock_response = MagicMock(status_code=200)
        monkeypatch.setattr(backup.requests, 'get', MagicMock(return_value=mock_response))
        mock_settings = MagicMock()
        mock_settings.QDRANT_URL = 'http://localhost'
        monkeypatch.setattr(backup, 'settings', mock_settings)

        backup.wait_for_qdrant_ready()

        backup.requests.get.assert_called_once_with('http://localhost/collections')

    def test_restore_backups_dispatches_to_restore_functions(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.BASE_DIR = str(tmp_path)
        mock_settings.DATA_DIR = str(tmp_path / 'data' / 'file.txt')
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'wait_for_postgres_ready', MagicMock())
        monkeypatch.setattr(backup, 'wait_for_qdrant_ready', MagicMock())

        date_str = '01012026'
        backup_date_dir = tmp_path / 'cache' / 'backups' / date_str
        backup_date_dir.mkdir(parents=True)
        (backup_date_dir / 'postgres_backup_1.sql.gpg').write_text('dummy')
        (backup_date_dir / 'data_backup_1.tar.gz.gpg').write_text('dummy')
        (backup_date_dir / 'qdrant_backup_1.tar.gz.gpg').write_text('dummy')

        restore_postgres = MagicMock()
        restore_tar = MagicMock()
        monkeypatch.setattr(backup, 'restore_postgres_in_memory', restore_postgres)
        monkeypatch.setattr(backup, 'restore_tar_in_memory', restore_tar)

        backup.restore_backups(date_str=date_str, passphrase='secret', second_pass=True)

        restore_postgres.assert_called_once()
        assert restore_tar.call_count == 2
        restore_tar.assert_any_call(str(backup_date_dir / 'data_backup_1.tar.gz.gpg'), 'secret', str(tmp_path / 'data'))
        restore_tar.assert_any_call(str(backup_date_dir / 'qdrant_backup_1.tar.gz.gpg'), 'secret', '/qdrant/storage')

    def test_main_performs_backups_and_cleanup(self, monkeypatch):
        monkeypatch.setenv('BACKUP_PASSPHRASE', 'secret')

        monkeypatch.setattr(backup, 'backup_postgres', MagicMock(return_value='postgres.sql'))
        monkeypatch.setattr(backup, 'backup_data', MagicMock(return_value='data.tar.gz'))
        monkeypatch.setattr(backup, 'backup_qdrant', MagicMock(return_value='qdrant.tar.gz'))
        monkeypatch.setattr(backup, 'encrypt_file', MagicMock(side_effect=['postgres.sql.gpg', 'data.tar.gz.gpg', 'qdrant.tar.gz.gpg']))
        cleanup_mock = MagicMock()
        monkeypatch.setattr(backup, 'cleanup_old_backups', cleanup_mock)

        backup.main()

        backup.backup_postgres.assert_called_once()
        backup.backup_data.assert_called_once()
        backup.backup_qdrant.assert_called_once()
        cleanup_mock.assert_called_once()

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

    def test_backup_postgres_error(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.POSTGRES_HOST = 'localhost'
        mock_settings.POSTGRES_PORT = 5432
        mock_settings.POSTGRES_USER = 'user'
        mock_settings.POSTGRES_DB = 'db'
        mock_settings.POSTGRES_PASSWORD = 'pass'
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'get_backup_dir', lambda date_folder=True: str(tmp_path))

        mock_run = MagicMock(side_effect=backup.subprocess.CalledProcessError(1, 'pg_dump'))
        monkeypatch.setattr(backup.subprocess, 'run', mock_run)

        with pytest.raises(backup.subprocess.CalledProcessError):
            backup.backup_postgres()

    def test_backup_data_error(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.DATA_DIR = str(tmp_path / 'non_existent_data_dir')
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'get_backup_dir', lambda date_folder=True: str(tmp_path))

        # tarfile opening or adding non-existent directory will raise an error
        with pytest.raises(Exception):
            backup.backup_data()

    def test_backup_qdrant_file_not_found(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.QDRANT_URL = 'http://localhost'
        mock_settings.QDRANT_STORAGE_DIR = str(tmp_path / 'non_existent_qdrant_storage')
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'get_backup_dir', lambda date_folder=True: str(tmp_path))

        client = MagicMock()
        client.get_collections.return_value = SimpleNamespace(collections=[SimpleNamespace(name='test_collection')])
        client.create_snapshot.return_value = 'snapshot-id'

        fake_module = MagicMock()
        fake_module.QdrantClient.return_value = client
        monkeypatch.setitem(sys.modules, 'qdrant_client', fake_module)

        with pytest.raises(FileNotFoundError):
            backup.backup_qdrant()

    def test_backup_qdrant_generic_error(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.QDRANT_URL = 'http://localhost'
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)

        client = MagicMock()
        client.get_collections.side_effect = Exception("Qdrant generic error")

        fake_module = MagicMock()
        fake_module.QdrantClient.return_value = client
        monkeypatch.setitem(sys.modules, 'qdrant_client', fake_module)

        with pytest.raises(Exception):
            backup.backup_qdrant()

    def test_encrypt_file_error(self, tmp_path, monkeypatch):
        gpg_instance = MagicMock()
        gpg_instance.encrypt_file.side_effect = Exception("Encryption error")
        gpg_class = MagicMock(return_value=gpg_instance)
        monkeypatch.setattr(backup.gnupg, 'GPG', gpg_class)

        with pytest.raises(Exception):
            backup.encrypt_file(str(tmp_path / 'non_existent.txt'), 'pass')

    def test_decrypt_file_non_gpg_suffix(self, tmp_path, monkeypatch):
        file_path = tmp_path / 'encrypted.dec'
        file_path.write_bytes(b'data')

        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.return_value = MagicMock(ok=True, status='decrypted', data=b'restored-bytes')
        gpg_class = MagicMock(return_value=gpg_instance)
        monkeypatch.setattr(backup.gnupg, 'GPG', gpg_class)

        decrypted_path = backup.decrypt_file(str(file_path), 'pass')
        assert decrypted_path.endswith('encrypted.dec.dec')

    def test_decrypt_file_not_ok(self, tmp_path, monkeypatch):
        file_path = tmp_path / 'encrypted.gpg'
        file_path.write_bytes(b'data')

        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.return_value = MagicMock(ok=False, status='Decryption failed status')
        gpg_class = MagicMock(return_value=gpg_instance)
        monkeypatch.setattr(backup.gnupg, 'GPG', gpg_class)

        with pytest.raises(ValueError):
            backup.decrypt_file(str(file_path), 'pass')

    def test_decrypt_file_exception(self, tmp_path, monkeypatch):
        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.side_effect = Exception("Decryption exception")
        gpg_class = MagicMock(return_value=gpg_instance)
        monkeypatch.setattr(backup.gnupg, 'GPG', gpg_class)

        with pytest.raises(Exception):
            backup.decrypt_file(str(tmp_path / 'non_existent.gpg'), 'pass')

    def test_restore_postgres_in_memory_not_ok(self, tmp_path, monkeypatch):
        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.return_value = MagicMock(ok=False, status='Decryption failed status')
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        encrypted_path = tmp_path / 'backup.sql.gpg'
        encrypted_path.write_text('encrypted')

        with pytest.raises(ValueError):
            backup.restore_postgres_in_memory(str(encrypted_path), 'pass')

    def test_restore_postgres_in_memory_drop_recreate_error(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.POSTGRES_HOST = 'localhost'
        mock_settings.POSTGRES_PORT = 5432
        mock_settings.POSTGRES_USER = 'user'
        mock_settings.POSTGRES_DB = 'db'
        mock_settings.POSTGRES_PASSWORD = 'pass'
        monkeypatch.setattr(backup, 'settings', mock_settings)

        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.return_value = MagicMock(ok=True, status='decrypted', data=b'SELECT 1;')
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.communicate.return_value = (b'', b'failed to drop recreate database')
        monkeypatch.setattr(backup.subprocess, 'Popen', MagicMock(return_value=process_mock))

        encrypted_path = tmp_path / 'backup.sql.gpg'
        encrypted_path.write_text('encrypted')

        with pytest.raises(Exception) as exc:
            backup.restore_postgres_in_memory(str(encrypted_path), 'pass')
        assert "Failed to drop/recreate database" in str(exc.value)

    def test_restore_postgres_in_memory_psql_error(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.POSTGRES_HOST = 'localhost'
        mock_settings.POSTGRES_PORT = 5432
        mock_settings.POSTGRES_USER = 'user'
        mock_settings.POSTGRES_DB = 'db'
        mock_settings.POSTGRES_PASSWORD = 'pass'
        monkeypatch.setattr(backup, 'settings', mock_settings)

        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.return_value = MagicMock(ok=True, status='decrypted', data=b'SELECT 1;')
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        # First call succeeds (drop/recreate), second call fails (restore)
        call_count = [0]
        def popen_side_effect(*args, **kwargs):
            call_count[0] += 1
            process_mock = MagicMock()
            if call_count[0] == 1:
                # First call: drop/recreate succeeds
                process_mock.returncode = 0
                process_mock.communicate.return_value = (b'', b'')
            else:
                # Second call: restore fails
                process_mock.returncode = 1
                process_mock.communicate.return_value = (b'', b'some psql stderr')
            return process_mock

        monkeypatch.setattr(backup.subprocess, 'Popen', MagicMock(side_effect=popen_side_effect))

        encrypted_path = tmp_path / 'backup.sql.gpg'
        encrypted_path.write_text('encrypted')

        with pytest.raises(Exception) as exc:
            backup.restore_postgres_in_memory(str(encrypted_path), 'pass')
        assert "psql error" in str(exc.value)

    def test_restore_postgres_in_memory_exception(self, tmp_path, monkeypatch):
        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.side_effect = Exception("Error decrypting")
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        encrypted_path = tmp_path / 'backup.sql.gpg'
        encrypted_path.write_text('encrypted')

        with pytest.raises(Exception):
            backup.restore_postgres_in_memory(str(encrypted_path), 'pass')

    def test_restore_tar_in_memory_not_ok(self, tmp_path, monkeypatch):
        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.return_value = MagicMock(ok=False, status='Decryption failed status')
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        encrypted_path = tmp_path / 'backup.tar.gz.gpg'
        encrypted_path.write_text('encrypted')

        with pytest.raises(ValueError):
            backup.restore_tar_in_memory(str(encrypted_path), 'pass', str(tmp_path))

    def test_restore_tar_in_memory_exception(self, tmp_path, monkeypatch):
        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.side_effect = Exception("Error decrypting")
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        encrypted_path = tmp_path / 'backup.tar.gz.gpg'
        encrypted_path.write_text('encrypted')

        with pytest.raises(Exception):
            backup.restore_tar_in_memory(str(encrypted_path), 'pass', str(tmp_path))

    def test_wait_for_postgres_ready_timeout(self, monkeypatch):
        monkeypatch.setattr(backup.psycopg2, 'connect', MagicMock(side_effect=Exception("DB not ready yet")))
        monkeypatch.setattr(backup.time, 'sleep', lambda x: None)

        with pytest.raises(Exception) as exc:
            backup.wait_for_postgres_ready()
        assert "PostgreSQL not ready after" in str(exc.value)

    def test_wait_for_qdrant_ready_timeout(self, monkeypatch):
        mock_response = MagicMock(status_code=500)
        monkeypatch.setattr(backup.requests, 'get', MagicMock(return_value=mock_response))
        monkeypatch.setattr(backup.time, 'sleep', lambda x: None)
        mock_settings = MagicMock()
        mock_settings.QDRANT_URL = 'http://localhost'
        monkeypatch.setattr(backup, 'settings', mock_settings)

        with pytest.raises(Exception) as exc:
            backup.wait_for_qdrant_ready()
        assert "Qdrant not ready after" in str(exc.value)

    def test_wait_for_qdrant_ready_exception(self, monkeypatch):
        monkeypatch.setattr(backup.requests, 'get', MagicMock(side_effect=Exception("Network error")))
        monkeypatch.setattr(backup.time, 'sleep', lambda x: None)
        mock_settings = MagicMock()
        mock_settings.QDRANT_URL = 'http://localhost'
        monkeypatch.setattr(backup, 'settings', mock_settings)

        with pytest.raises(Exception) as exc:
            backup.wait_for_qdrant_ready()
        assert "Qdrant not ready after" in str(exc.value)

    def test_restore_backups_no_passphrase(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'wait_for_postgres_ready', MagicMock())
        monkeypatch.setattr(backup, 'wait_for_qdrant_ready', MagicMock())
        monkeypatch.delenv('BACKUP_PASSPHRASE', raising=False)

        with pytest.raises(ValueError) as exc:
            backup.restore_backups(date_str='01012026')
        assert "BACKUP_PASSPHRASE not set" in str(exc.value)

    def test_restore_backups_directory_not_found(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'wait_for_postgres_ready', MagicMock())
        monkeypatch.setattr(backup, 'wait_for_qdrant_ready', MagicMock())

        with pytest.raises(FileNotFoundError) as exc:
            backup.restore_backups(date_str='01012026', passphrase='pass')
        assert "No backups found for date" in str(exc.value)

    def test_restore_backups_skips_non_gpg_and_raises(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'wait_for_postgres_ready', MagicMock())
        monkeypatch.setattr(backup, 'wait_for_qdrant_ready', MagicMock())

        date_str = '01012026'
        backup_date_dir = tmp_path / 'cache' / 'backups' / date_str
        backup_date_dir.mkdir(parents=True)
        # Create non-.gpg file to test skipping
        (backup_date_dir / 'readme.txt').write_text('info')
        # Create .gpg file that triggers error on restore to test raising exception
        (backup_date_dir / 'postgres_backup_1.sql.gpg').write_text('dummy')

        restore_postgres = MagicMock(side_effect=Exception("Failed to restore DB"))
        monkeypatch.setattr(backup, 'restore_postgres_in_memory', restore_postgres)

        with pytest.raises(Exception) as exc:
            backup.restore_backups(date_str=date_str, passphrase='pass')
        assert "Failed to restore DB" in str(exc.value)

    def test_main_missing_passphrase(self, monkeypatch):
        monkeypatch.delenv('BACKUP_PASSPHRASE', raising=False)
        with pytest.raises(ValueError) as exc:
            backup.main()
        assert "BACKUP_PASSPHRASE not set" in str(exc.value)

    def test_main_generic_error(self, monkeypatch):
        monkeypatch.setenv('BACKUP_PASSPHRASE', 'secret')
        monkeypatch.setattr(backup, 'backup_postgres', MagicMock(side_effect=Exception("Postgres failed")))

        with pytest.raises(Exception) as exc:
            backup.main()
        assert "Postgres failed" in str(exc.value)

    def test_cleanup_old_backups_skips_non_dir_and_decrypted(self, tmp_path, monkeypatch):
        base_dir = tmp_path / 'cache' / 'backups'
        base_dir.mkdir(parents=True)

        decrypted_folder = base_dir / 'DECRYPTED'
        decrypted_folder.mkdir()
        file_path = base_dir / 'some_file.txt'
        file_path.write_text('hello')

        # This should not raise and should keep decrypted_folder and file_path
        backup.cleanup_old_backups(days=7, base_dir=str(base_dir))
        assert decrypted_folder.exists()
        assert file_path.exists()

    def test_cleanup_old_backups_error(self, tmp_path, monkeypatch):
        # Passing non-existent base_dir without ignore might raise/log error, let's verify raise
        with pytest.raises(Exception):
            backup.cleanup_old_backups(days=7, base_dir=str(tmp_path / 'non_existent_directory_error'))

    def test_restore_tar_in_memory_clears_subdirectory(self, tmp_path, monkeypatch):
        # Setup source tar
        encrypted_path = tmp_path / 'backup.tar.gz.gpg'
        encrypted_path.write_text('encrypted')

        tar_bytes = io.BytesIO()
        with tarfile.open(fileobj=tar_bytes, mode='w:gz') as tar:
            content = tmp_path / 'hello.txt'
            content.write_text('hello')
            tar.add(str(content), arcname='hello.txt')
        tar_bytes.seek(0)

        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.return_value = MagicMock(ok=True, status='decrypted', data=tar_bytes.getvalue())
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        # Setup extract path with existing items to be cleared
        extract_path = tmp_path / 'extract'
        extract_path.mkdir()
        sub_dir = extract_path / 'sub'
        sub_dir.mkdir()
        old_file = extract_path / 'old.txt'
        old_file.write_text('old')

        # Test successful clearing and extraction
        backup.restore_tar_in_memory(str(encrypted_path), 'passphrase', str(extract_path))
        assert (extract_path / 'hello.txt').read_text() == 'hello'
        assert not sub_dir.exists()
        assert not old_file.exists()

        # Test exception path during clearing
        extract_path2 = tmp_path / 'extract2'
        extract_path2.mkdir()
        unremovable_file = extract_path2 / 'unremovable.txt'
        unremovable_file.write_text('stuck')

        # Mock os.remove to raise exception when deleting unremovable_file
        orig_remove = os.remove
        def mock_remove(path):
            if 'unremovable.txt' in str(path):
                raise OSError("Permission denied")
            return orig_remove(path)
        monkeypatch.setattr(backup.os, 'remove', mock_remove)

        backup.restore_tar_in_memory(str(encrypted_path), 'passphrase', str(extract_path2))
        # Unremovable file exception is caught and logged, other extraction proceeds
        assert (extract_path2 / 'hello.txt').read_text() == 'hello'

    def test_restore_tar_in_memory_clears_app_data(self, tmp_path, monkeypatch):
        encrypted_path = tmp_path / 'backup.tar.gz.gpg'
        encrypted_path.write_text('encrypted')

        gpg_instance = MagicMock()
        gpg_instance.decrypt_file.return_value = MagicMock(ok=True, status='decrypted', data=b'fake-tar-data')
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        # Mock tarfile.open to avoid actual extraction to /app
        fake_tar = MagicMock()
        fake_tar_ctx = MagicMock()
        fake_tar_ctx.__enter__ = MagicMock(return_value=fake_tar)
        fake_tar_ctx.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr(backup.tarfile, 'open', MagicMock(return_value=fake_tar_ctx))

        # Mock os.path.exists to return True for /app and /app/data to trigger lines 225-239
        orig_exists = os.path.exists
        def exists_mock(path):
            return True if str(path).replace('\\', '/') in ['/app', '/app/data'] else orig_exists(path)
        monkeypatch.setattr(backup.os.path, 'exists', exists_mock)

        orig_listdir = os.listdir
        def listdir_mock(path):
            return ['sub', 'old.txt'] if str(path).replace('\\', '/') == '/app/data' else orig_listdir(path)
        monkeypatch.setattr(backup.os, 'listdir', listdir_mock)

        orig_isdir = os.path.isdir
        def isdir_mock(path):
            return True if str(path).replace('\\', '/') == '/app/data/sub' else orig_isdir(path)
        monkeypatch.setattr(backup.os.path, 'isdir', isdir_mock)

        # Mock shutil.rmtree to raise error for 'sub' to cover lines 238-239 exception handling
        rmtree_calls = []
        def rmtree_mock(path):
            rmtree_calls.append(path)
            if 'sub' in str(path):
                raise OSError("Permission denied")
        monkeypatch.setattr(shutil, 'rmtree', rmtree_mock)

        remove_calls = []
        def remove_mock(path):
            remove_calls.append(path)
        monkeypatch.setattr(backup.os, 'remove', remove_mock)

        backup.restore_tar_in_memory(str(encrypted_path), 'passphrase', '/app')

        # 'sub' is a dir, so rmtree is called on it
        assert len(rmtree_calls) == 1
        assert 'sub' in str(rmtree_calls[0])
        # 'old.txt' is a file, so remove is called on it
        assert len(remove_calls) == 1
        assert 'old.txt' in str(remove_calls[0])

    def test_restore_backups_with_default_date(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)
        monkeypatch.setattr(backup, 'wait_for_postgres_ready', MagicMock())
        monkeypatch.setattr(backup, 'wait_for_qdrant_ready', MagicMock())

        original_datetime = datetime.datetime
        # Mock datetime to return a fixed date
        class FixedDateTime:
            @classmethod
            def now(cls):
                return original_datetime(2026, 1, 1)
        monkeypatch.setattr(backup.datetime, 'datetime', FixedDateTime)

        # Ensure directory does not exist to raise FileNotFoundError with today's date
        with pytest.raises(FileNotFoundError) as exc:
            backup.restore_backups(date_str=None, passphrase='pass')
        assert "01012026" in str(exc.value)

    def test_cleanup_old_backups_with_default_base_dir(self, tmp_path, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.BASE_DIR = str(tmp_path)
        monkeypatch.setattr(backup, 'settings', mock_settings)

        # Create cache/backups directory structure
        backups_dir = tmp_path / 'cache' / 'backups'
        backups_dir.mkdir(parents=True)
        old_folder = backups_dir / '01012026'
        old_folder.mkdir()
        recent_folder = backups_dir / '02012026'
        recent_folder.mkdir()

        old_mtime = time.time() - (10 * 86400)
        recent_mtime = time.time()
        os.utime(old_folder, (old_mtime, old_mtime))
        os.utime(recent_folder, (recent_mtime, recent_mtime))

        backup.cleanup_old_backups(days=7, base_dir=None)

        assert not old_folder.exists()
        assert recent_folder.exists()

    def test_run_as_main(self, tmp_path, monkeypatch):
        import builtins
        import runpy
        monkeypatch.setenv('BACKUP_PASSPHRASE', 'secret')

        # Mock settings BASE_DIR to use tmp_path
        mock_settings = MagicMock()
        mock_settings.BASE_DIR = str(tmp_path)
        mock_settings.POSTGRES_HOST = 'localhost'
        mock_settings.POSTGRES_PORT = 5432
        mock_settings.POSTGRES_USER = 'user'
        mock_settings.POSTGRES_DB = 'db'
        mock_settings.POSTGRES_PASSWORD = 'pass'
        mock_settings.DATA_DIR = str(tmp_path / 'data')
        mock_settings.QDRANT_URL = 'http://localhost'
        mock_settings.QDRANT_STORAGE_DIR = str(tmp_path / 'qdrant_storage')
        monkeypatch.setattr(backup, 'settings', mock_settings)
        # Patch config.settings module settings object as well since runpy loads config.settings
        from config import settings as config_settings
        monkeypatch.setattr(config_settings, 'settings', mock_settings)

        # Create directories
        (tmp_path / 'data').mkdir()
        (tmp_path / 'qdrant_storage').mkdir()
        (tmp_path / 'qdrant_storage' / 'col').write_text('dummy')

        # Mock subprocess.run
        mock_run = MagicMock()
        monkeypatch.setattr(backup.subprocess, 'run', mock_run)

        # Mock tarfile.open
        fake_tar = MagicMock()
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_tar
        monkeypatch.setattr(backup.tarfile, 'open', MagicMock(return_value=fake_context))

        # Mock qdrant_client
        client = MagicMock()
        client.get_collections.return_value = SimpleNamespace(collections=[SimpleNamespace(name='col')])
        client.create_snapshot.return_value = 'snap'
        fake_module = MagicMock()
        fake_module.QdrantClient.return_value = client
        monkeypatch.setitem(sys.modules, 'qdrant_client', fake_module)

        # Mock gnupg.GPG
        gpg_instance = MagicMock()
        gpg_instance.encrypt_file.return_value = MagicMock(data=b'encrypted')
        monkeypatch.setattr(backup.gnupg, 'GPG', MagicMock(return_value=gpg_instance))

        # Mock builtins.open to return fake file content for the files backup service tries to read
        orig_open = builtins.open
        def mock_open(file, mode='r', *args, **kwargs):
            if any(term in str(file) for term in ['postgres_backup', 'data_backup', 'qdrant_backup']):
                return io.BytesIO(b'dummy content')
            return orig_open(file, mode, *args, **kwargs)
        monkeypatch.setattr(builtins, 'open', mock_open)

        # Mock os.remove
        monkeypatch.setattr(backup.os, 'remove', MagicMock())

        # Run using run_path to completely avoid sys.modules package parent/submodule warning
        script_path = os.path.join('src', 'services', 'backup.py')
        runpy.run_path(script_path, run_name='__main__')

        # Verify pg_dump subprocess run was indeed called
        assert mock_run.called


