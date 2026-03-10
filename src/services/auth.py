from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import hashlib
import base64
import bcrypt
import uuid
from uuid import UUID
from sqlalchemy.orm import Session
from config.settings import settings
from shared.database.models.user import User
from config.logger import logger


class AuthService:
    def __init__(self):
        # Usar bcrypt diretamente para evitar problemas com passlib
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def _prepare_password_for_bcrypt(self, password: str) -> str:
        """
        Prepara senha para bcrypt usando SHA-256 para lidar com o limite de 72 bytes.
        Isso mantém a segurança enquanto permite senhas longas.
        """
        # SHA-256 produz sempre 32 bytes (256 bits), que está dentro do limite do bcrypt
        sha256_hash = hashlib.sha256(password.encode('utf-8')).digest()
        # Base64 encode para string (44 caracteres, bem abaixo do limite de 72)
        return base64.b64encode(sha256_hash).decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica se a senha plain corresponde ao hash"""
        # Verificar se precisa de reset (compatibilidade com migração)
        if hashed_password.startswith("RESET_REQUIRED_"):
            return False  # Sempre falha para forçar reset
        
        prepared_password = self._prepare_password_for_bcrypt(plain_password)
        
        try:
            # Usar bcrypt diretamente
            return bcrypt.checkpw(prepared_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False

    def needs_password_reset(self, hashed_password: str) -> bool:
        """Verifica se a senha precisa ser resetada"""
        return hashed_password.startswith("RESET_REQUIRED_")

    def get_password_hash(self, password: str) -> str:
        """Gera hash da senha"""
        prepared_password = self._prepare_password_for_bcrypt(password)
        
        try:
            # Gerar salt e hash usando bcrypt diretamente
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(prepared_password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Error hashing password: {str(e)}")
            raise

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Cria token JWT de acesso"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "type": "access"
        })
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Cria token JWT de atualização"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "type": "refresh"
        })
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verifica e decodifica token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verificar tipo do token
            if payload.get("type") != token_type:
                logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
                return None
            
            # Verificar expiração
            exp = payload.get("exp")
            if exp is None or datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                logger.warning("Token expired")
                return None
                
            return payload
        except JWTError as e:
            logger.warning(f"JWT error: {str(e)}")
            return None

    def authenticate_user(self, user_repo: Any, email: str, password: str) -> Optional[User]:
        """Autentica usuário com email e senha"""
        # Buscar por email
        user = user_repo.get_by_email(email)
        
        if not user:
            logger.warning(f"User not found: {email}")
            return None
        
        if not self.verify_password(password, user.password_hash):
            logger.warning(f"Invalid password for user: {email}")
            return None
            
        logger.info(f"User authenticated successfully: {email}")
        return user

    def create_user_tokens(self, user: User, user_repo: Any) -> Dict[str, Any]:
        """Cria tokens de acesso e refresh para o usuário e os registra no banco"""
        access_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email
        }
        
        refresh_data = {
            "sub": str(user.id),
            "username": user.username
        }
        
        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        refresh_token_expires = timedelta(days=self.refresh_token_expire_days)
        
        access_token = self.create_access_token(access_data, expires_delta=access_token_expires)
        refresh_token = self.create_refresh_token(refresh_data)
        
        # Registrar no banco de dados
        now = datetime.now(timezone.utc)
        user_repo.create_token(
            user_id=user.id,
            token=access_token,
            token_type="access",
            expires_at=now + access_token_expires
        )
        user_repo.create_token(
            user_id=user.id,
            token=refresh_token,
            token_type="refresh",
            expires_at=now + refresh_token_expires
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }

    def refresh_access_token(self, refresh_token: str, user_repo: Any) -> Optional[Dict[str, Any]]:
        """Gera novo access token usando refresh token, verificando no banco"""
        # Verificar se o refresh token existe e está ativo no banco
        stored_token = user_repo.get_token(refresh_token)
        if not stored_token or stored_token.token_type != "refresh":
            return None

        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            return None
        
        # Criar novo access token
        access_data = {
            "sub": payload["sub"],
            "username": payload["username"],
            "email": payload.get("email", "")
        }
        
        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        new_access_token = self.create_access_token(access_data, expires_delta=access_token_expires)
        
        # Registrar novo access token no banco
        user_repo.create_token(
            user_id=stored_token.user_id,
            token=new_access_token,
            token_type="access",
            expires_at=datetime.now(timezone.utc) + access_token_expires
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }

    def get_current_user_from_token(self, token: str, user_repo: Any) -> Optional[User]:
        """Obtém usuário atual a partir do token, verificando se está ativo no banco"""
        # Verificar se o token existe e está ativo no banco
        stored_token = user_repo.get_token(token)
        if not stored_token or not stored_token.is_active:
            logger.warning("Attempt to use inactive or non-existent token")
            return None

        payload = self.verify_token(token, "access")
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if user_id is None:
            return None
        
        try:
            # Convert string to UUID
            user_uuid = UUID(user_id)
            user = user_repo.get_by_id(user_uuid)
            return user
        except ValueError:
            logger.warning(f"Invalid UUID in token sub: {user_id}")
            return None


# Instância global do serviço
auth_service = AuthService()
