from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from shared.database.session import get_db
from shared.database.models.user import User
from src.repositories.user import UserRepository
from src.services.auth import auth_service
from config.logger import logger


# Configuração do esquema de segurança
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Obtém o usuário atual a partir do token JWT
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """
    Obtém o usuário atual se houver token, mas não falha se não houver
    Útil para endpoints que podem ser acessados com ou sem autenticação
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        user_repo = UserRepository(db)
        user = auth_service.get_current_user_from_token(token, user_repo)
        return user
    except Exception:
        return None
