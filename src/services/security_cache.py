import os
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
from pathlib import Path
from config.logger import logger
from config.settings import settings


class SecurityCache:
    """
    Sistema de cache em arquivos para tracking de segurança
    """
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir or os.path.join(settings.BASE_DIR, "cache", "security"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivos de cache
        self.login_attempts_file = self.cache_dir / "login_attempts.json"
        self.ip_tracking_file = self.cache_dir / "ip_tracking.json"
        self.user_tracking_file = self.cache_dir / "user_tracking.json"
        self.anomalies_file = self.cache_dir / "anomalies.json"
        
        # Configurações personalizáveis
        self.multiple_ip_threshold = getattr(settings, 'MULTIPLE_IP_THRESHOLD', 3)
        self.multiple_user_threshold = getattr(settings, 'MULTIPLE_USER_THRESHOLD', 5)
        self.rapid_attempts_threshold = getattr(settings, 'RAPID_ATTEMPTS_THRESHOLD', 10)
        self.consecutive_failures_threshold = getattr(settings, 'CONSECUTIVE_FAILURES_THRESHOLD', 3)
        self.ip_block_threshold = getattr(settings, 'IP_BLOCK_THRESHOLD', 15)
        
        # Inicializar arquivos se não existirem
        self._init_cache_files()
        
        # Configurações de tempo
        self.cleanup_interval = 3600  # 1 hora em segundos
        self.max_age_hours = 24  # Manter dados por 24 horas
        
    def _init_cache_files(self):
        """Inicializa arquivos de cache"""
        for file_path in [self.login_attempts_file, self.ip_tracking_file, 
                         self.user_tracking_file, self.anomalies_file]:
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump({}, f)
    
    def _load_cache(self, file_path: Path) -> Dict:
        """Carrega cache do arquivo"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading cache from {file_path}: {str(e)}")
            return {}
    
    def _save_cache(self, file_path: Path, data: Dict):
        """Salva cache no arquivo"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving cache to {file_path}: {str(e)}")
    
    def record_login_attempt(self, email: str, ip_address: str, user_agent: str,
                           success: bool, failure_reason: str = None,
                           risk_score: str = "LOW", anomalies: List[str] = None):
        """Registra tentativa de login no cache"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Carregar tentativas existentes
        attempts = self._load_cache(self.login_attempts_file)
        
        # Adicionar nova tentativa
        attempt_id = f"{email}_{int(time.time())}"
        attempts[attempt_id] = {
            "timestamp": timestamp,
            "email": email,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "success": success,
            "failure_reason": failure_reason,
            "risk_score": risk_score,
            "anomalies": anomalies or [],
            "unix_timestamp": time.time()
        }
        
        # Salvar
        self._save_cache(self.login_attempts_file, attempts)
        
        # Atualizar tracking
        self._update_ip_tracking(ip_address, email, timestamp)
        self._update_user_tracking(email, ip_address, timestamp)
        
        # Se houver anomalias, registrar
        if anomalies:
            self._record_anomaly(email, ip_address, risk_score, anomalies, timestamp)
        
        logger.debug(f"Login attempt recorded: {email} from {ip_address} - {'SUCCESS' if success else 'FAILURE'}")
    
    def _update_ip_tracking(self, ip_address: str, email: str, timestamp: str):
        """Atualiza tracking de IPs"""
        ip_data = self._load_cache(self.ip_tracking_file)
        
        if ip_address not in ip_data:
            ip_data[ip_address] = {
                "first_seen": timestamp,
                "last_seen": timestamp,
                "emails": [],
                "attempt_count": 0,
                "success_count": 0,
                "failure_count": 0
            }
        
        # Atualizar dados
        ip_data[ip_address]["last_seen"] = timestamp
        ip_data[ip_address]["attempt_count"] += 1
        
        if email not in ip_data[ip_address]["emails"]:
            ip_data[ip_address]["emails"].append(email)
        
        self._save_cache(self.ip_tracking_file, ip_data)
    
    def _update_user_tracking(self, email: str, ip_address: str, timestamp: str):
        """Atualiza tracking de usuários"""
        user_data = self._load_cache(self.user_tracking_file)
        
        if email not in user_data:
            user_data[email] = {
                "first_seen": timestamp,
                "last_seen": timestamp,
                "ips": [],
                "attempt_count": 0,
                "success_count": 0,
                "failure_count": 0
            }
        
        # Atualizar dados
        user_data[email]["last_seen"] = timestamp
        user_data[email]["attempt_count"] += 1
        
        if ip_address not in user_data[email]["ips"]:
            user_data[email]["ips"].append(ip_address)
        
        self._save_cache(self.user_tracking_file, user_data)
    
    def _record_anomaly(self, email: str, ip_address: str, risk_score: str, 
                       anomalies: List[str], timestamp: str):
        """Registra anomalia detectada"""
        anomalies_data = self._load_cache(self.anomalies_file)
        
        anomaly_id = f"{email}_{int(time.time())}"
        anomalies_data[anomaly_id] = {
            "timestamp": timestamp,
            "email": email,
            "ip_address": ip_address,
            "risk_score": risk_score,
            "anomalies": anomalies,
            "unix_timestamp": time.time()
        }
        
        self._save_cache(self.anomalies_file, anomalies_data)
    
    def detect_anomalies(self, email: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """Detecta anomalias baseado nos dados em cache"""
        anomalies = []
        risk_score = "LOW"
        
        # Carregar dados
        user_data = self._load_cache(self.user_tracking_file)
        ip_data = self._load_cache(self.ip_tracking_file)
        attempts = self._load_cache(self.login_attempts_file)
        
        current_time = time.time()
        
        # 1. Verificar múltiplos IPs para mesmo usuário (últimas 24h)
        if email in user_data:
            user_ips = user_data[email]["ips"]
            if len(user_ips) > self.multiple_ip_threshold:
                anomalies.append(f"Múltiplos IPs detectados: {len(user_ips)} em 24h")
                risk_score = "HIGH"
        
        # 2. Verificar múltiplos usuários para mesmo IP (última hora)
        if ip_address in ip_data:
            ip_emails = ip_data[ip_address]["emails"]
            if len(ip_emails) > self.multiple_user_threshold:
                anomalies.append(f"Múltiplos usuários no IP: {len(ip_emails)} em 1h")
                risk_score = "HIGH" if risk_score == "LOW" else "CRITICAL"
        
        # 3. Verificar tentativas rápidas (último minuto)
        recent_attempts = [
            attempt for attempt in attempts.values()
            if attempt["ip_address"] == ip_address and 
            current_time - attempt["unix_timestamp"] <= 60
        ]
        
        if len(recent_attempts) > self.rapid_attempts_threshold:
            anomalies.append(f"Tentativas rápidas: {len(recent_attempts)} em 1 minuto")
            risk_score = "CRITICAL"
        
        # 4. Verificar User-Agent suspeito
        suspicious_agents = ["curl", "wget", "python-requests", "bot", "scanner"]
        ua_lower = user_agent.lower()
        
        if not user_agent or len(user_agent) < 10:
            anomalies.append("User-Agent ausente ou muito curto")
            risk_score = "MEDIUM" if risk_score == "LOW" else risk_score
        else:
            for suspicious in suspicious_agents:
                if suspicious in ua_lower:
                    anomalies.append(f"User-Agent suspeito: {suspicious}")
                    risk_score = "MEDIUM" if risk_score == "LOW" else risk_score
                    break
        
        # 5. Verificar falhas consecutivas
        recent_failures = [
            attempt for attempt in attempts.values()
            if attempt["email"] == email and 
            not attempt["success"] and
            current_time - attempt["unix_timestamp"] <= 300  # 5 minutos
        ]
        
        if len(recent_failures) > self.consecutive_failures_threshold:
            anomalies.append(f"Falhas consecutivas: {len(recent_failures)} em 5 minutos")
            risk_score = "HIGH" if risk_score == "LOW" else "CRITICAL"
        
        return {
            "risk_score": risk_score,
            "anomalies": anomalies,
            "is_anomaly": len(anomalies) > 0,
            "anomaly_details": "; ".join(anomalies) if anomalies else None
        }
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Gera resumo de segurança"""
        cutoff_time = time.time() - (hours * 3600)
        
        attempts = self._load_cache(self.login_attempts_file)
        anomalies_data = self._load_cache(self.anomalies_file)
        
        # Filtrar dados recentes
        recent_attempts = [
            attempt for attempt in attempts.values()
            if attempt["unix_timestamp"] > cutoff_time
        ]
        
        recent_anomalies = [
            anomaly for anomaly in anomalies_data.values()
            if anomaly["unix_timestamp"] > cutoff_time
        ]
        
        # Estatísticas
        total_attempts = len(recent_attempts)
        successful_attempts = len([a for a in recent_attempts if a["success"]])
        failed_attempts = total_attempts - successful_attempts
        
        risk_counts = {}
        for attempt in recent_attempts:
            risk = attempt.get("risk_score", "LOW")
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        unique_ips = len(set(a["ip_address"] for a in recent_attempts))
        unique_emails = len(set(a["email"] for a in recent_attempts))
        
        return {
            "time_range_hours": hours,
            "total_login_attempts": total_attempts,
            "successful_logins": successful_attempts,
            "failed_logins": failed_attempts,
            "anomalies_detected": len(recent_anomalies),
            "risk_distribution": risk_counts,
            "unique_ips": unique_ips,
            "unique_emails": unique_emails,
            "success_rate": (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0
        }
    
    def cleanup_old_data(self):
        """Limpa dados antigos do cache"""
        cutoff_time = time.time() - (self.max_age_hours * 3600)
        
        # Limpar tentativas antigas
        attempts = self._load_cache(self.login_attempts_file)
        filtered_attempts = {
            k: v for k, v in attempts.items()
            if v["unix_timestamp"] > cutoff_time
        }
        self._save_cache(self.login_attempts_file, filtered_attempts)
        
        # Limpar anomalias antigas
        anomalies = self._load_cache(self.anomalies_file)
        filtered_anomalies = {
            k: v for k, v in anomalies.items()
            if v["unix_timestamp"] > cutoff_time
        }
        self._save_cache(self.anomalies_file, filtered_anomalies)
        
        # Limpar tracking de IPs (manter apenas recentes)
        ip_data = self._load_cache(self.ip_tracking_file)
        filtered_ip_data = {}
        for ip, data in ip_data.items():
            last_seen = data.get("unix_timestamp", 0)
            if last_seen > cutoff_time:
                filtered_ip_data[ip] = data
        
        self._save_cache(self.ip_tracking_file, filtered_ip_data)
        
        # Limpar tracking de usuários
        user_data = self._load_cache(self.user_tracking_file)
        filtered_user_data = {}
        for email, data in user_data.items():
            last_seen = data.get("unix_timestamp", 0)
            if last_seen > cutoff_time:
                filtered_user_data[email] = data
        
        self._save_cache(self.user_tracking_file, filtered_user_data)
        
        logger.info(f"Security cache cleanup completed. Removed data older than {self.max_age_hours} hours")
    
    def get_recent_anomalies(self, hours: int = 1) -> List[Dict]:
        """Retorna anomalias recentes"""
        cutoff_time = time.time() - (hours * 3600)
        anomalies_data = self._load_cache(self.anomalies_file)
        
        recent_anomalies = [
            anomaly for anomaly in anomalies_data.values()
            if anomaly["unix_timestamp"] > cutoff_time
        ]
        
        # Ordenar por timestamp (mais recentes primeiro)
        recent_anomalies.sort(key=lambda x: x["unix_timestamp"], reverse=True)
        
        return recent_anomalies
    
    def should_block_ip(self, ip_address: str) -> tuple[bool, Optional[str]]:
        """Verifica se IP deve ser bloqueado baseado em atividades recentes"""
        ip_data = self._load_cache(self.ip_tracking_file)
        attempts = self._load_cache(self.login_attempts_file)
        
        if ip_address not in ip_data:
            return False, None
        
        # Verificar tentativas recentes
        current_time = time.time()
        recent_attempts = [
            attempt for attempt in attempts.values()
            if attempt["ip_address"] == ip_address and
            current_time - attempt["unix_timestamp"] <= 300  # 5 minutos
        ]
        
        # Se muitas tentativas falhas, bloquear
        failed_attempts = len([a for a in recent_attempts if not a["success"]])
        if failed_attempts > self.ip_block_threshold:
            return True, f"IP bloqueado por excesso de tentativas falhas: {failed_attempts}"
        
        return False, None


# Instância global
security_cache = SecurityCache()
