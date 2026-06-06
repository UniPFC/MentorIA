import logging
from shared.database.session import SessionLocal
from shared.database.models.user import User, UserLevel
from src.services.auth import auth_service
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_e2e_admin():
    """
    Cria estritamente o usuário administrador para testes E2E.
    Executa em milissegundos sem carregar modelos de IA ou vazar dados.
    """
    db = SessionLocal()
    try:
        system_email = settings.SYSTEM_USER_EMAIL or "system@techstein.ai"
        system_username = "MentorIA"

        # Verifica se o usuário já existe
        user = db.query(User).filter(User.email == system_email).first()
        
        if not user:
            logger.info("Injetando usuário Admin de testes no banco...")
            user = User(
                email=system_email,
                username=system_username,
                password_hash=auth_service.get_password_hash(settings.SYSTEM_USER_PASSWORD or "change-this-password"),
                is_active=True,
                level=UserLevel.LEVEL_05, # Nível Máximo (Admin)
                token_budget=None
            )
            db.add(user)
            db.commit()
            logger.info("Usuário Admin de testes injetado com sucesso!")
        else:
            logger.info("Usuário Admin já existe no ambiente.")
    except Exception as e:
        logger.error(f"Erro ao injetar usuário de teste: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_e2e_admin()