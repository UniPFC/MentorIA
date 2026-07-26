from unittest.mock import MagicMock, patch

import pytest
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from src.api.main import app, lifespan


@pytest.mark.unit
class TestMain:
    def test_root(self):
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "RAG Chat API"
        assert response.json()["version"] == "1.0.0"
        assert response.json()["docs"] == "/docs"

    def test_health(self):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_add_stt_header(self):
        client = TestClient(app)
        response = client.get("/")
        assert "x-stt-enabled" in response.headers

    @pytest.mark.asyncio
    async def test_lifespan_seeder_exception(self):
        with patch("src.api.main.run_migrations"):
            with patch(
                "src.api.main.settings"
            ) as mock_settings:  # Mock AUTO_RUN_SEEDER para rodar o seeder
                mock_settings.AUTO_RUN_SEEDER = True
                with patch(
                    "src.api.main.seed_default_knowledge",
                    side_effect=Exception("Seeder failed"),
                ):
                    async with lifespan(app):
                        pass

    @pytest.mark.asyncio
    async def test_validation_exception_handler_password_string_should_have(self):
        """Cobre o elif 'String should have at least' (linhas 73-74)"""
        request = MagicMock()
        exc = RequestValidationError(
            errors=[
                {
                    "loc": ("body", "password"),
                    "msg": "String should have at least 1 uppercase",
                    "type": "value_error",
                }
            ]
        )
        handler = app.exception_handlers[RequestValidationError]
        response = await handler(request, exc)
        assert response.status_code == 422
        data = response.body.decode()
        assert "Senha deve ter no mínimo 8 caracteres" in data

    @pytest.mark.asyncio
    async def test_validation_exception_handler_password_min_chars(self):
        """Cobre o if 'at least 8 characters' (linhas 71-72)"""
        request = MagicMock()
        exc = RequestValidationError(
            errors=[
                {
                    "loc": ("body", "new_password"),
                    "msg": "Value error, at least 8 characters",
                    "type": "value_error",
                }
            ]
        )
        handler = app.exception_handlers[RequestValidationError]
        response = await handler(request, exc)
        assert response.status_code == 422
        data = response.body.decode()
        assert "Senha deve ter no mínimo 8 caracteres" in data
