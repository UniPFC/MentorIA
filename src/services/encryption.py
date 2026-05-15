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
        self.backend = default_backend()
        self.master_key = self._get_master_key()

    def _get_master_key(self) -> bytes:
        """Deriva chave AES-256 a partir do SECRET_KEY"""
        if not settings.SECRET_KEY:
            raise ValueError("SECRET_KEY is not set")

        if not settings.ENCRYPTION_SALT:
            raise ValueError("ENCRYPTION_SALT is not set")

        secret = settings.SECRET_KEY.encode("utf-8")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=settings.ENCRYPTION_SALT.encode("utf-8"),
            iterations=100000,
            backend=self.backend,
        )

        return kdf.derive(secret)

    def _looks_encrypted(self, value: str) -> bool:
        """Validação básica de base64 + tamanho mínimo AES-GCM"""
        if not value or not isinstance(value, str):
            return False

        try:
            decoded = base64.b64decode(value, validate=True)
            return len(decoded) >= 44  # nonce(12) + tag(16) + ciphertext
        except Exception:
            return False

    def encrypt(self, data: str) -> str:
        """Criptografa dados usando AES-256-GCM"""
        if data is None or data == "":
            return data

        try:
            nonce = os.urandom(12)

            cipher = Cipher(
                algorithms.AES(self.master_key),
                modes.GCM(nonce),
                backend=self.backend,
            )

            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(data.encode("utf-8")) + encryptor.finalize()

            encrypted = nonce + encryptor.tag + ciphertext

            return base64.b64encode(encrypted).decode("utf-8")

        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise ValueError("Encryption failed") from e

    def decrypt(self, encrypted_data: str) -> str:
        """Descriptografa dados AES-256-GCM"""
        if not encrypted_data:
            return encrypted_data

        if not self._looks_encrypted(encrypted_data):
            raise ValueError("Data does not appear to be encrypted")

        try:
            raw = base64.b64decode(encrypted_data)

            nonce = raw[:12]
            tag = raw[12:28]
            ciphertext = raw[28:]

            cipher = Cipher(
                algorithms.AES(self.master_key),
                modes.GCM(nonce, tag),
                backend=self.backend,
            )

            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            return plaintext.decode("utf-8")

        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise ValueError("Decryption failed") from e

    def encrypt_field(self, field_name: str, value: str) -> str:
        try:
            encrypted = self.encrypt(value)
            logger.debug(f"Encrypted field: {field_name}")
            return encrypted
        except Exception as e:
            logger.error(f"Failed encrypt field {field_name}: {e}")
            raise

    def decrypt_field(self, field_name: str, encrypted_value: str) -> str:
        try:
            decrypted = self.decrypt(encrypted_value)
            logger.debug(f"Decrypted field: {field_name}")
            return decrypted
        except Exception as e:
            logger.error(f"Failed decrypt field {field_name}: {e}")
            raise


# Instância global
encryption_service = EncryptionService()


def encrypt_sensitive_data(data: str) -> str:
    return encryption_service.encrypt(data)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    return encryption_service.decrypt(encrypted_data)


def is_encrypted_data(value: str) -> bool:
    return encryption_service._looks_encrypted(value)