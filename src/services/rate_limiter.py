from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
import time
from collections import defaultdict
from config.logger import logger


class SimpleRateLimiter:
    """
    Implementação simples de rate limiting em memória
    """
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 5, block_minutes: int = 10):
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self.block_minutes = block_minutes
        self.attempts: Dict[str, list] = defaultdict(list)
        self.blocks: Dict[str, datetime] = {}
    
    def _cleanup_old_attempts(self, key: str):
        """Remove tentativas antigas da janela de tempo"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=self.window_minutes)
        self.attempts[key] = [
            attempt_time for attempt_time in self.attempts[key]
            if attempt_time > cutoff_time
        ]
    
    def is_blocked(self, key: str) -> tuple[bool, Optional[int]]:
        """
        Verifica se uma chave está bloqueada
        Retorna (bloqueado, minutos_restantes)
        """
        if key in self.blocks:
            block_expiry = self.blocks[key]
            if datetime.now(timezone.utc) < block_expiry:
                remaining_minutes = int((block_expiry - datetime.now(timezone.utc)).total_seconds() / 60)
                return True, remaining_minutes
            else:
                # Bloqueio expirou
                del self.blocks[key]
                if key in self.attempts:
                    del self.attempts[key]
        
        return False, None
    
    def check_attempt(self, key: str) -> tuple[bool, Optional[int]]:
        """
        Verifica se pode fazer uma tentativa
        Retorna (permitido, minutos_restantes_se_bloqueado)
        """
        # Verificar se está bloqueado
        blocked, remaining = self.is_blocked(key)
        if blocked:
            return False, remaining
        
        # Limpar tentativas antigas
        self._cleanup_old_attempts(key)
        
        # Verificar se excedeu o limite
        if len(self.attempts[key]) >= self.max_attempts:
            # Bloquear
            block_expiry = datetime.now(timezone.utc) + timedelta(minutes=self.block_minutes)
            self.blocks[key] = block_expiry
            
            remaining_minutes = self.block_minutes
            logger.warning(f"Rate limit exceeded for {key}. Blocked for {remaining_minutes} minutes.")
            return False, remaining_minutes
        
        return True, None
    
    def record_attempt(self, key: str):
        """Registra uma tentativa falha"""
        self.attempts[key].append(datetime.now(timezone.utc))
    
    def record_success(self, key: str):
        """Registra sucesso e limpa tentativas"""
        if key in self.attempts:
            del self.attempts[key]
        if key in self.blocks:
            del self.blocks[key]
    
    def get_remaining_attempts(self, key: str) -> int:
        """Retorna número de tentativas restantes"""
        blocked, _ = self.is_blocked(key)
        if blocked:
            return 0
        
        self._cleanup_old_attempts(key)
        return max(0, self.max_attempts - len(self.attempts[key]))


# Instância global usando configurações do settings
from config.settings import settings
rate_limiter = SimpleRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_minutes=settings.LOGIN_WINDOW_MINUTES,
    block_minutes=settings.LOGIN_BLOCK_MINUTES
)
