from unittest.mock import patch

import pytest

from src.services.encryption import (
    EncryptionService,
    decrypt_sensitive_data,
    encrypt_sensitive_data,
    is_encrypted_data,
)


@pytest.mark.unit
class TestEncryptionService:
    """Testes unitários para o serviço de criptografia"""

    def test_init_success(self):
        """Testa inicialização do serviço com sucesso"""
        service = EncryptionService()
        assert service.master_key is not None
        assert len(service.master_key) == 32

    def test_init_missing_secret_key(self):
        """Testa inicialização sem SECRET_KEY"""
        with patch("src.services.encryption.settings") as mock_settings:
            mock_settings.SECRET_KEY = None
            mock_settings.ENCRYPTION_SALT = "salt"
            with pytest.raises(ValueError) as exc_info:
                EncryptionService()
            assert "SECRET_KEY is not set" in str(exc_info.value)

    def test_init_missing_encryption_salt(self):
        """Testa inicialização sem ENCRYPTION_SALT"""
        with patch("src.services.encryption.settings") as mock_settings:
            mock_settings.SECRET_KEY = "secret"
            mock_settings.ENCRYPTION_SALT = None
            with pytest.raises(ValueError) as exc_info:
                EncryptionService()
            assert "ENCRYPTION_SALT is not set" in str(exc_info.value)

    def test_encrypt_empty_or_none(self):
        """Testa criptografia com string vazia ou None"""
        service = EncryptionService()
        assert service.encrypt(None) is None
        assert service.encrypt("") == ""

    def test_encrypt_decrypt_success(self):
        """Testa fluxo completo de criptografia e decriptação"""
        service = EncryptionService()
        original_text = "Dados extremamente secretos 123!"

        encrypted = service.encrypt(original_text)
        assert encrypted != original_text
        assert service._looks_encrypted(encrypted) is True

        decrypted = service.decrypt(encrypted)
        assert decrypted == original_text

    def test_looks_encrypted_false(self):
        """Testa _looks_encrypted com dados inválidos"""
        service = EncryptionService()
        assert service._looks_encrypted(None) is False
        assert service._looks_encrypted("") is False
        assert service._looks_encrypted("not_base64_!") is False
        assert service._looks_encrypted("YQ==") is False  # Muito curto

    def test_encrypt_exception(self):
        """Testa exceção durante criptografia"""
        service = EncryptionService()
        with patch("os.urandom", side_effect=Exception("urandom error")):
            with pytest.raises(ValueError) as exc_info:
                service.encrypt("data")
            assert "Encryption failed" in str(exc_info.value)

    def test_decrypt_empty_or_none(self):
        """Testa decriptação de dados vazios ou None"""
        service = EncryptionService()
        assert service.decrypt(None) is None
        assert service.decrypt("") == ""

    def test_decrypt_invalid_format(self):
        """Testa decriptação de formato inválido"""
        service = EncryptionService()
        with pytest.raises(ValueError) as exc_info:
            service.decrypt("texto_nao_criptografado")
        assert "Data does not appear to be encrypted" in str(exc_info.value)

    def test_decrypt_exception(self):
        """Testa exceção durante decriptação"""
        service = EncryptionService()
        original_text = "Dados"
        encrypted = service.encrypt(original_text)

        # Simular falha corrompendo a chave
        with patch.object(service, "master_key", b"invalid_key_length_32_bytes_xyz"):
            with pytest.raises(ValueError) as exc_info:
                service.decrypt(encrypted)
            assert "Decryption failed" in str(exc_info.value)

    def test_encrypt_field_success(self):
        """Testa criptografia de campo com sucesso"""
        service = EncryptionService()
        encrypted = service.encrypt_field("password", "minhasenha")
        assert encrypted != "minhasenha"

    def test_encrypt_field_exception(self):
        """Testa exceção ao criptografar campo"""
        service = EncryptionService()
        with patch.object(service, "encrypt", side_effect=Exception("Error")):
            with pytest.raises(Exception):
                service.encrypt_field("password", "minhasenha")

    def test_decrypt_field_success(self):
        """Testa decriptação de campo com sucesso"""
        service = EncryptionService()
        encrypted = service.encrypt("minhasenha")
        decrypted = service.decrypt_field("password", encrypted)
        assert decrypted == "minhasenha"

    def test_decrypt_field_exception(self):
        """Testa exceção ao decodificar campo"""
        service = EncryptionService()
        with patch.object(service, "decrypt", side_effect=Exception("Error")):
            with pytest.raises(Exception):
                service.decrypt_field("password", "encrypted_data")

    def test_global_helper_functions(self):
        """Testa funções auxiliares globais"""
        original_text = "Dados globais"
        encrypted = encrypt_sensitive_data(original_text)
        assert encrypted != original_text
        assert is_encrypted_data(encrypted) is True

        decrypted = decrypt_sensitive_data(encrypted)
        assert decrypted == original_text
