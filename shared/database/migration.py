from alembic.config import Config
from alembic import command
from config.settings import settings
from config.logger import logger

def run_migrations():
    """Run Alembic migrations to upgrade the database to the latest version."""
    try:
        logger.info("Starting database migrations...")
        alembic_cfg = Config("/app/alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", settings.POSTGRES_URL)
        
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully.")
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")