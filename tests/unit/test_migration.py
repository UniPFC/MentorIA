from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
class TestMigration:
    """Testes unitários para database migration"""

    def test_run_migrations_success(self):
        """Testa execução de migrações com sucesso"""
        from shared.database.migration import run_migrations

        with patch('shared.database.migration.Config') as mock_config, \
             patch('shared.database.migration.command') as mock_command, \
             patch('shared.database.migration.logger') as mock_logger, \
             patch('shared.database.migration.settings') as mock_settings:

            mock_cfg = Mock()
            mock_config.return_value = mock_cfg
            mock_settings.POSTGRES_URL = "postgresql://user:pass@localhost/db"

            run_migrations()

            called_path = mock_config.call_args[0][0]
            assert called_path.endswith("alembic.ini"), f"Expected path ending in alembic.ini, got: {called_path}"
            mock_cfg.set_main_option.assert_called_once_with("sqlalchemy.url", "postgresql://user:pass@localhost/db")
            mock_command.upgrade.assert_called_once_with(mock_cfg, "head")
            mock_logger.info.assert_called()

    def test_run_migrations_error(self):
        """Testa execução de migrações com erro"""
        from shared.database.migration import run_migrations

        with patch('shared.database.migration.Config') as mock_config, \
             patch('shared.database.migration.command') as mock_command, \
             patch('shared.database.migration.logger') as mock_logger, \
             patch('shared.database.migration.settings') as mock_settings:

            mock_cfg = Mock()
            mock_config.return_value = mock_cfg
            mock_settings.POSTGRES_URL = "postgresql://user:pass@localhost/db"
            mock_command.upgrade.side_effect = Exception("Alembic error")

            with pytest.raises(Exception, match="Alembic error"):
                run_migrations()

            mock_logger.error.assert_called_once()
