"""
Serviço de criptografia para dados sensíveis
Usa AES-256-GCM para criptografia simétrica
"""

import base64
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from config.logger import logger
from config.settings import settings


class EncryptionService:
    """
    Serviço para criptografia e decriptação de dados sensíveis
    """
    
    def __init__(self):
        """Inicializa o serviço com a chave principal"""
        self.backend = default_backend()
        self.master_key = self._get_master_key()
    
    def _get_master_key(self) -> bytes:
        """
        Obtém a chave mestre do ambiente ou gera uma
        """
        # Usar SECRET_KEY como base para a chave de criptografia
        secret = settings.SECRET_KEY.encode('utf-8')
        
        # Derivar chave de 32 bytes (256 bits) usando PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=settings.ENCRYPTION_SALT.encode('utf-8'),  # Salt do settings
            iterations=100000,
            backend=self.backend
        )
        return kdf.derive(secret)
    
    def encrypt(self, data: str) -> str:
        """
        Criptografa dados sensíveis
        
        Args:
            data: Dado em plain text para criptografar
            
        Returns:
            Dado criptografado em base64
        """
        if not data:
            return data
        
        try:
            # Gerar nonce aleatório para cada criptografia
            nonce = os.urandom(12)  # 96 bits para GCM
            
            # Criar cipher
            cipher = Cipher(
                algorithms.AES(self.master_key),
                modes.GCM(nonce),
                backend=self.backend
            )
            
            # Criptografar
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(data.encode('utf-8')) + encryptor.finalize()
            
            # Combinar nonce + ciphertext + tag para armazenamento
            encrypted_data = nonce + encryptor.tag + ciphertext
            
            # Retornar em base64 para armazenamento seguro
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise ValueError(f"Failed to encrypt data: {e}")
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decriptografa dados sensíveis
        
        Args:
            encrypted_data: Dado criptografado em base64
            
        Returns:
            Dado em plain text
        """
        if not encrypted_data:
            return encrypted_data
        
        try:
            # Decodificar base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extrair nonce, tag e ciphertext
            nonce = encrypted_bytes[:12]  # Primeiros 12 bytes
            tag = encrypted_bytes[12:28]  # Próximos 16 bytes
            ciphertext = encrypted_bytes[28:]  # Restante
            
            # Criar cipher
            cipher = Cipher(
                algorithms.AES(self.master_key),
                modes.GCM(nonce, tag),
                backend=self.backend
            )
            
            # Decriptografar
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")
    
    def encrypt_field(self, field_name: str, value: str) -> str:
        """
        Criptografa um campo específico com logging
        
        Args:
            field_name: Nome do campo para logging
            value: Valor para criptografar
            
        Returns:
            Valor criptografado
        """
        try:
            encrypted = self.encrypt(value)
            logger.debug(f"Encrypted field {field_name}")
            return encrypted
        except Exception as e:
            logger.error(f"Failed to encrypt field {field_name}: {e}")
            raise
    
    def decrypt_field(self, field_name: str, encrypted_value: str) -> str:
        """
        Decriptografa um campo específico com logging
        
        Args:
            field_name: Nome do campo para logging
            encrypted_value: Valor criptografado
            
        Returns:
            Valor decriptografado
        """
        try:
            decrypted = self.decrypt(encrypted_value)
            logger.debug(f"Decrypted field {field_name}")
            return decrypted
        except Exception as e:
            logger.error(f"Failed to decrypt field {field_name}: {e}")
            raise


# Instância global do serviço de criptografia
encryption_service = EncryptionService()


def encrypt_sensitive_data(data: str) -> str:
    """
    Função helper para criptografar dados sensíveis
    
    Args:
        data: Dado para criptografar
        
    Returns:
        Dado criptografado
    """
    return encryption_service.encrypt(data)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Função helper para decriptografar dados sensíveis
    
    Args:
        encrypted_data: Dado criptografado
        
    Returns:
        Dado decriptografado
    """
    return encryption_service.decrypt(encrypted_data)
