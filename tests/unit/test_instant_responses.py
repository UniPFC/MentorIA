import pytest
from src.services.instant_responses import InstantResponseService

class TestInstantResponseService:
    def test_normalize_text(self):
        # Test basic normalization
        assert InstantResponseService.normalize_text("Olá Mundo!") == "ola mundo"
        # Test accents removal
        assert InstantResponseService.normalize_text("Ação e Reação") == "acao e reacao"
        # Test punctuation removal
        assert InstantResponseService.normalize_text("Oi, tudo bem?") == "oi tudo bem"
        # Test multiple spaces
        assert InstantResponseService.normalize_text("  muito    espaco  ") == "muito espaco"
        # Test mixed casing
        assert InstantResponseService.normalize_text("PyThOn") == "python"

    def test_get_instant_response_exact_match(self):
        # "oi" is a known key in INSTANT_RESPONSES
        response = InstantResponseService.get_instant_response("Oi!")
        assert response == "Olá! Como posso ajudá-lo?"

    def test_get_instant_response_with_accents(self):
        # Testing a phrase that has variations in the dict
        response = InstantResponseService.get_instant_response("COMO VOCÊ ESTÁ?")
        assert "perfeitamente" in response.lower()

    def test_get_instant_response_partial_match(self):
        # Test if it matches a pattern contained in the question
        # "obrigado" is a pattern, the input is "Muito obrigado pela ajuda"
        response = InstantResponseService.get_instant_response("Muito obrigado pela ajuda")
        assert response == "De nada! Estou aqui para ajudar. Tem mais alguma dúvida?"

    def test_get_instant_response_no_match(self):
        response = InstantResponseService.get_instant_response("Qual a cor do cavalo branco de Napoleão?")
        assert response is None
