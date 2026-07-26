import os

from alembic.config import Config

from alembic import command  # type: ignore
from config.logger import logger
from config.settings import settings


def run_migrations():
    """Run Alembic migrations to upgrade the database to the latest version."""
    try:
        logger.info("Starting database migrations...")
        alembic_ini = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "alembic.ini",
        )
        alembic_cfg = Config(alembic_ini)
        alembic_cfg.set_main_option("sqlalchemy.url", settings.POSTGRES_URL)

        logger.info("Running upgrade command...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Upgrade command completed.")

        logger.info("Database migrations applied successfully.")
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        raise
