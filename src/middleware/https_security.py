from fastapi import Request, Response
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from config.logger import logger
from config.settings import settings


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware para forçar HTTPS em produção
    """
    
    async def dispatch(self, request: Request, call_next):
        # Em desenvolvimento, não forçar HTTPS
        if settings.DEV_MODE:
            return await call_next(request)
        
        # Verificar se já é HTTPS
        if request.url.scheme != "https":
            # Construir URL HTTPS
            https_url = request.url.replace(scheme="https")
            logger.info(f"Redirecting HTTP to HTTPS: {request.url} -> {https_url}")
            return Response(
                status_code=301,
                headers={"Location": str(https_url)}
            )
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware para adicionar headers de segurança
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Em desenvolvimento, headers mais relaxados
        if settings.DEV_MODE:
            return response
        
        # Headers de segurança
        security_headers = {
            # HSTS - Força HTTPS por 1 ano
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Prevenção de clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevenção de MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Política de referer
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Prevenção de XSS
            "X-XSS-Protection": "1; mode=block",
            
            # Política de conteúdo (opcional, pode precisar ajuste)
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
            
            # Prevenção de man-in-the-middle
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        # Adicionar headers à resposta
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class SecureCookieMiddleware(BaseHTTPMiddleware):
    """
    Middleware para garantir cookies seguros em produção
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Em desenvolvimento, cookies podem ser menos restritos
        if settings.DEV_MODE:
            return response
        
        # Garantir que cookies sejam seguros
        # Note: FastAPI já define secure=True quando HTTPS é detectado
        # Este middleware garante consistência
        for cookie_name, cookie_value in response.headers.items():
            if cookie_name.lower().startswith('set-cookie'):
                # Garantir flags de segurança em cookies
                if 'secure=' not in cookie_value.lower():
                    cookie_value += '; Secure'
                if 'httponly=' not in cookie_value.lower():
                    cookie_value += '; HttpOnly'
                if 'samesite=' not in cookie_value.lower():
                    cookie_value += '; SameSite=Strict'
                
                response.headers[cookie_name] = cookie_value
        
        return response
