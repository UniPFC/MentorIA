from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from config.logger import logger
from config.settings import settings


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware para proteção CSRF com fastapi-csrf-protect
    """
    
    def __init__(self, app, csrf_protect: CsrfProtect):
        super().__init__(app)
        self.csrf_protect = csrf_protect
    
    async def dispatch(self, request: Request, call_next):
        # Em desenvolvimento, CSRF pode ser mais relaxado
        if settings.DEV_MODE:
            return await call_next(request)
        
        # Verificar se é uma requisição que precisa de proteção CSRF
        if self._needs_csrf_protection(request):
            try:
                # Validar CSRF token
                await self.csrf_protect.validate_csrf(request)
            except CsrfProtectError as e:
                logger.warning(f"CSRF protection triggered: {e}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token inválido ou ausente",
                    headers={"X-CSRF-Error": "invalid_token"}
                )
        
        return await call_next(request)
    
    def _needs_csrf_protection(self, request: Request) -> bool:
        """
        Verifica se a requisição precisa de proteção CSRF
        """
        # Métodos que não precisam de CSRF (seguros por natureza)
        safe_methods = {"GET", "HEAD", "OPTIONS", "TRACE"}
        
        if request.method in safe_methods:
            return False
        
        # Rotas de autenticação que não precisam de CSRF
        # (login, register, etc. - geralmente feitas via API)
        auth_paths = ["/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh"]
        
        if any(request.url.path.startswith(path) for path in auth_paths):
            return False
        
        # Rotas públicas que não precisam de CSRF
        public_paths = ["/", "/health", "/docs", "/openapi.json"]
        
        if any(request.url.path in path for path in public_paths):
            return False
        
        # Headers de API (indicam chamadas de API, não de formulário)
        if "x-api-key" in request.headers or "authorization" in request.headers:
            return False
        
        # Content-Type application/json (API calls)
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            return False
        
        # Para todos os outros casos (formulários web), exigir CSRF
        return True


# Configuração do CSRF Protection
def create_csrf_protect() -> CsrfProtect:
    """
    Cria e configura a instância de CSRF protection
    """
    csrf_config = CsrfProtect()
    
    # Configurar secrets para CSRF tokens
    csrf_config._secret_key = settings.SECRET_KEY
    
    # Configurar cookie settings
    csrf_config._cookie_name = settings.CSRF_COOKIE_NAME
    csrf_config._cookie_samesite = "strict"
    csrf_config._cookie_secure = not settings.DEV_MODE  # Secure apenas em produção
    csrf_config._cookie_httponly = True
    
    # Configurar header name para o token
    csrf_config._header_name = "X-CSRF-Token"
    
    # Configurar tempo de expiração (1 hora)
    csrf_config._csrf_token_age = settings.CSRF_TOKEN_AGE
    
    return csrf_config
