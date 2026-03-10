from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from shared.database.session import get_db
from shared.database.models.user import User
from src.repositories.user import UserRepository
from src.api.schemas.auth import (
    UserRegister, UserLogin, Token, TokenRefresh, TokenVerifyResponse,
    UserResponse, LogoutResponse, PasswordReset, AdminPasswordReset
)
from src.api.dependencies import get_current_active_user, security
from src.services.auth import auth_service
from config.logger import logger


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Registra um novo usuário
    """
    user_repo = UserRepository(db)

    # Verificar se username já existe
    existing_user = user_repo.get_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de usuário já existe"
        )
    
    # Verificar se email já existe
    existing_email = user_repo.get_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )
    
    # Criar novo usuário
    hashed_password = auth_service.get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password
    )
    
    user_repo.create(new_user)
    
    logger.info(f"User registered successfully: {new_user.username}")
    return new_user


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Autentica usuário e retorna tokens JWT
    """
    user_repo = UserRepository(db)
    
    user = auth_service.authenticate_user(user_repo, user_credentials.email, user_credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar se precisa de reset de senha
    if auth_service.needs_password_reset(user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sua senha precisa ser redefinida. Entre em contato com o administrador.",
            headers={"WWW-Authenticate": "Bearer", "X-Password-Reset-Required": "true"},
        )
    
    # Atualizar último login
    from datetime import datetime, timezone
    user.last_login = datetime.now(timezone.utc)
    user_repo.update(user)
    
    tokens = auth_service.create_user_tokens(user, user_repo)
    logger.info(f"User logged in successfully: {user.username}")
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """
    Atualiza o token de acesso usando refresh token
    """
    user_repo = UserRepository(db)
    new_tokens = auth_service.refresh_access_token(token_data.refresh_token, user_repo)
    if not new_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info("Access token refreshed successfully")
    return {
        "access_token": new_tokens["access_token"],
        "refresh_token": token_data.refresh_token,  # Mantém o mesmo refresh token
        "token_type": new_tokens["token_type"],
        "expires_in": new_tokens["expires_in"]
    }


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Realiza logout do usuário invalidando o token no banco de dados
    """
    token = credentials.credentials
    user_repo = UserRepository(db)
    user_repo.invalidate_token(token)
    
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Logout realizado com sucesso", "success": True}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Obtém informações do usuário atual
    """
    return current_user


@router.post("/verify-token", response_model=TokenVerifyResponse)
async def verify_token(current_user: User = Depends(get_current_active_user)):
    """
    Verifica se o token é válido
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username
    }


@router.post("/reset-password")
async def reset_password(
    password_data: PasswordReset,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Reset de senha do próprio usuário
    """
    # Verificar senha atual
    if not auth_service.verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta"
        )
    
    # Atualizar senha
    current_user.password_hash = auth_service.get_password_hash(password_data.new_password)
    user_repo = UserRepository(db)
    user_repo.update(current_user)
    
    logger.info(f"Password reset successfully for user: {current_user.username}")
    return {"message": "Senha atualizada com sucesso", "success": True}


@router.post("/admin-reset-password")
async def admin_reset_password(
    password_data: AdminPasswordReset,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Reset de senha por administrador (apenas user ID 1 pode usar)
    """
    user_repo = UserRepository(db)

    # Verificar se é admin (simplificado - apenas user admin)
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem resetar senhas de outros usuários"
        )
    
    # Buscar usuário
    user = user_repo.get_by_id(password_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Atualizar senha
    user.password_hash = auth_service.get_password_hash(password_data.new_password)
    user_repo.update(user)
    
    logger.info(f"Admin reset password for user: {user.username} by admin: {current_user.username}")
    return {"message": f"Senha do usuário '{user.username}' atualizada com sucesso", "success": True}