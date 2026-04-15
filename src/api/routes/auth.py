from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from shared.database.session import get_db
from shared.database.models.user import User
from src.repositories.user import UserRepository
from src.api.schemas.auth import (
    UserRegister, UserLogin, Token, TokenRefresh, TokenVerifyResponse,
    UserResponse, LogoutResponse, PasswordResetRequest, PasswordResetConfirm
)
from src.api.dependencies import get_current_active_user, get_user_repo, security
from src.services.auth import auth_service
from src.services.email import email_service
from src.services.security_cache import security_cache
from config.logger import logger
from config.settings import settings
from datetime import datetime, timedelta, timezone


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Registra um novo usuário
    """

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

async def login(user_credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """
    Autentica usuário e retorna tokens JWT
    """
    # Obter informações da requisição
    client_ip = _get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    
    # Verificar se IP está bloqueado pelo cache de segurança
    ip_blocked, ip_block_reason = security_cache.should_block_ip(client_ip)
    if ip_blocked:
        security_cache.record_login_attempt(
            user_credentials.email, client_ip, user_agent,
            False, ip_block_reason, "HIGH", [ip_block_reason]
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="IP temporariamente bloqueado por atividades suspeitas.",
            headers={"Retry-After": "300"}
        )
    
    # Detectar anomalias antes da autenticação
    anomaly_result = security_cache.detect_anomalies(user_credentials.email, client_ip, user_agent)
    
    # Se detectar anomalias críticas ou rate limit, bloquear
    if anomaly_result['risk_score'] in ['CRITICAL', 'HIGH']:
        security_cache.record_login_attempt(
            user_credentials.email, client_ip, user_agent,
            False, "Security anomaly detected", anomaly_result['risk_score'], anomaly_result['anomalies']
        )
        
        # Se for CRITICAL, bloquear imediatamente
        if anomaly_result['risk_score'] == 'CRITICAL':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso bloqueado por motivos de segurança.",
                headers={"X-Security-Block": "anomaly_detection"}
            )
        
        # Se for HIGH, dar rate limit
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas suspeitas. Tente novamente mais tarde.",
            headers={"Retry-After": "300"}
        )
    
    user_repo = UserRepository(db)
    
    user = auth_service.authenticate_user(user_repo, user_credentials.email, user_credentials.password)
    
    if not user:
        # Registrar tentativa falha com anomalias
        security_cache.record_login_attempt(
            user_credentials.email, client_ip, user_agent,
            False, "Email ou senha incorretos", 
            anomaly_result['risk_score'], anomaly_result['anomalies']
        )
        
        # Verificar se agora tem anomalia pós-falha
        post_failure_anomaly = security_cache.detect_anomalies(user_credentials.email, client_ip, user_agent)
        if post_failure_anomaly['risk_score'] in ['CRITICAL', 'HIGH']:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Número excessivo de tentativas. Tente novamente mais tarde.",
                headers={"Retry-After": "300"}
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Login bem-sucedido - registrar com anomalias
    security_cache.record_login_attempt(
        user_credentials.email, client_ip, user_agent,
        True, None, anomaly_result['risk_score'], anomaly_result['anomalies']
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
    logger.info(f"User logged in successfully: {user.username} from {client_ip}")
    
    # Limpar cache antigo periodicamente
    security_cache.cleanup_old_data()
    
    return tokens


def _get_client_ip(request: Request) -> str:
    """
    Obtém o IP real do cliente considerando proxies
    """
    # Verificar headers comuns de proxy
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Pega o primeiro IP da lista
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback para o IP da conexão
    if hasattr(request, 'client') and request.client:
        return request.client.host
    
    return "unknown"


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Atualiza o token de acesso usando refresh token
    """
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
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Realiza logout do usuário invalidando o token e refresh tokens no banco de dados
    """
    token = credentials.credentials
    user_repo.invalidate_token(token)
    user_repo.invalidate_refresh_tokens(current_user.id)
    
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
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Solicita reset de senha via email
    """
    
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
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Confirma o reset de senha usando o token recebido por email
    """
    
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