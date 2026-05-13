import pytest
from src.services.instant_responses import InstantResponseService

@pytest.mark.unit
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

    def test_get_instant_response_exact_match_oi(self):
        # "oi" is a known key in INSTANT_RESPONSES
        response = InstantResponseService.get_instant_response("Oi!")
        assert response == "Olá! Como posso ajudá-lo?"

    def test_get_instant_response_exact_match_ola(self):
        # "ola" is a known key
        response = InstantResponseService.get_instant_response("Olá!")
        assert response == "Olá! Como posso ajudá-lo?"

    def test_get_instant_response_with_accents(self):
        # Testing a phrase that has variations in the dict
        response = InstantResponseService.get_instant_response("COMO VOCÊ ESTÁ?")
        assert "perfeitamente" in response.lower()

    def test_get_instant_response_no_partial_match(self):
        # Test that partial matches are NOT triggered
        # "como funciona" is a pattern, but "Me diga como funciona os triangulos..." should NOT match
        response = InstantResponseService.get_instant_response("Me diga como funciona os triangulos e quais questoes preciso saber")
        assert response is None

    def test_get_instant_response_no_match(self):
        response = InstantResponseService.get_instant_response("Qual a cor do cavalo branco de Napoleão?")
        assert response is None

    def test_get_instant_response_obrigado_exact(self):
        # "obrigado" should match exactly
        response = InstantResponseService.get_instant_response("Obrigado")
        assert response == "De nada! Estou aqui para ajudar. Tem mais alguma dúvida?"
        
        # But "Muito obrigado pela ajuda" should NOT match (partial)
        response = InstantResponseService.get_instant_response("Muito obrigado pela ajuda")
        assert response is None

    def test_get_instant_response_tchau(self):
        response = InstantResponseService.get_instant_response("Tchau!")
        assert response == "Até logo! Volte sempre que precisar de ajuda!"

    def test_get_instant_response_qual_seu_nome(self):
        response = InstantResponseService.get_instant_response("Qual seu nome?")
        assert "MentorIA" in response
