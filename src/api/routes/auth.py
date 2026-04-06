from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from shared.database.session import get_db
from shared.database.models.user import User
from src.repositories.user import UserRepository
from src.api.schemas.auth import (
    UserRegister, UserLogin, Token, TokenRefresh, TokenVerifyResponse,
    UserResponse, LogoutResponse, PasswordResetRequest, PasswordResetConfirm
)
from src.api.dependencies import get_current_active_user, security
from src.services.auth import auth_service
from src.services.email import email_service
from src.services.rate_limiter import rate_limiter
from config.logger import logger
from config.settings import settings
from datetime import datetime, timedelta, timezone


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Registra um novo usuário
    """
    user_repo = UserRepository(db)

    # Verificar se username é reservado (camada extra de segurança)
    if user_data.username.lower() == 'mentoria':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='O nome de usuário "MentorIA" é reservado para o sistema e não pode ser usado.'
        )

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
    # Verificar rate limit por email antes de processar
    allowed, remaining_minutes = rate_limiter.check_attempt(user_credentials.email)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas de login. Tente novamente em {remaining_minutes} minutos.",
            headers={"Retry-After": str(remaining_minutes * 60)}
        )
    
    user_repo = UserRepository(db)
    
    user = auth_service.authenticate_user(user_repo, user_credentials.email, user_credentials.password)
    
    if not user:
        # Registrar tentativa falha
        rate_limiter.record_attempt(user_credentials.email)
        
        # Verificar se agora está bloqueado após registrar esta tentativa
        blocked, block_minutes = rate_limiter.is_blocked(user_credentials.email)
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Número excessivo de tentativas. Conta bloqueada por {block_minutes} minutos.",
                headers={"Retry-After": str(block_minutes * 60)}
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Login bem-sucedido - limpar tentativas
    rate_limiter.record_success(user_credentials.email)
    
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
        "refresh_token": new_tokens["refresh_token"],  # Novo refresh token (rotation)
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
    Realiza logout do usuário invalidando todos os seus tokens no banco de dados
    """
    token = credentials.credentials
    user_repo = UserRepository(db)
    
    # Invalidar todos os tokens do usuário (access e refresh)
    user_repo.invalidate_all_user_tokens(current_user.id)
    
    logger.info(f"User logged out and all tokens invalidated: {current_user.username}")
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


@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Solicita reset de senha via email
    """
    user_repo = UserRepository(db)
    
    # Buscar usuário por email
    user = user_repo.get_by_email(request.email)
    if not user:
        # Por segurança, não revelamos se o email existe ou não
        logger.info(f"Password reset requested for non-existent email: {request.email}")
        return {"message": "Se o email estiver cadastrado, você receberá instruções para resetar sua senha", "success": True}
    
    # Gerar token de reset
    reset_token = email_service.generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    
    # Salvar token no banco
    user_repo.create_password_reset_token(user.id, reset_token, expires_at)
    
    # Enviar email
    email_sent = email_service.send_password_reset_email(user.email, user.username, reset_token)
    
    if email_sent:
        logger.info(f"Password reset email sent to user: {user.username}")
        return {"message": "Se o email estiver cadastrado, você receberá instruções para resetar sua senha", "success": True}
    else:
        logger.error(f"Failed to send password reset email to user: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao enviar email de reset de senha. Tente novamente mais tarde."
        )


@router.post("/confirm-reset-password")
async def confirm_reset_password(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirma o reset de senha usando o token recebido por email
    """
    user_repo = UserRepository(db)
    
    # Validar token
    reset_token_data = user_repo.get_password_reset_token(request.token)
    if not reset_token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado"
        )
    
    # Buscar usuário
    user = user_repo.get_by_id(reset_token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Atualizar senha
    user.password_hash = auth_service.get_password_hash(request.new_password)
    user_repo.update(user)
    
    # Invalidar token
    user_repo.invalidate_password_reset_token(request.token)
    
    # Enviar email de confirmação
    email_service.send_password_changed_email(user.email, user.username)
    
    logger.info(f"Password reset confirmed for user: {user.username}")
    return {"message": "Senha alterada com sucesso", "success": True}