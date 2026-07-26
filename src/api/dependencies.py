from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from config.logger import logger
from shared.database.models.user import User
from shared.database.session import get_db
from src.repositories.chat import ChatRepository
from src.repositories.chat_type import ChatTypeRepository
from src.repositories.chat_type_favorite import ChatTypeFavoriteRepository
from src.repositories.ingestion_job import IngestionJobRepository
from src.repositories.user import UserRepository
from src.services.auth import auth_service

# Configuração do esquema de segurança
security = HTTPBearer(auto_error=False)


# Repository Dependencies
def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    """Dependency to get User repository."""
    return UserRepository(db)


def get_chat_type_repo(db: Session = Depends(get_db)) -> ChatTypeRepository:
    """Dependency to get ChatType repository."""
    return ChatTypeRepository(db)


def get_chat_type_favorite_repo(
    db: Session = Depends(get_db),
) -> ChatTypeFavoriteRepository:
    """Dependency to get ChatTypeFavorite repository."""
    return ChatTypeFavoriteRepository(db)


def get_chat_repo(db: Session = Depends(get_db)) -> ChatRepository:
    """Dependency to get Chat repository."""
    return ChatRepository(db)


def get_ingestion_job_repo(db: Session = Depends(get_db)) -> IngestionJobRepository:
    """Dependency to get IngestionJob repository."""
    return IngestionJobRepository(db)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    logger.info(
        f"Checking auth for {request.url.path}. Cookies: {request.cookies.keys()}"
    )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = None
    if credentials:
        token = credentials.credentials
    if not token:
        token = request.cookies.get("authToken")

    if not token:
        raise credentials_exception

    try:
        user_repo = UserRepository(db)
        user = auth_service.get_current_user_from_token(token, user_repo)
        if user is None:
            raise credentials_exception
        return user
    except Exception as e:
        logger.warning(f"Authentication error: {str(e)}")
        raise credentials_exception


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Obtém o usuário atual ativo
    (pode ser expandido para verificar status, etc.)
    """
    return current_user


def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Obtém o usuário atual se houver token, mas não falha se não houver
    Útil para endpoints que podem ser acessados com ou sem autenticação
    """
    token = None
    if credentials:
        token = credentials.credentials
    if not token:
        token = request.cookies.get("authToken")

    if not token:
        return None

    try:
        user_repo = UserRepository(db)
        user = auth_service.get_current_user_from_token(token, user_repo)
        return user
    except Exception:
        return None
