"""
Service for handling instant responses to common questions.
Handles normalization of text (accents, capitalization, etc).
"""

import unicodedata
import re
from typing import Optional, Dict, List
from config.logger import logger


class InstantResponseService:
    """Service for managing and retrieving instant responses."""
    
    # Dictionary of instant responses
    # Key: normalized question patterns
    # Value: response text
    INSTANT_RESPONSES: Dict[str, str] = {
        # Example responses - expand as needed

        "oi": "Olá! Como posso ajudá-lo?",
        "ola": "Olá! Como posso ajudá-lo?",
        "oi tudo bem": "Tudo bem! Como posso ajudá-lo?",
        "ola tudo bem": "Tudo bem! Como posso ajudá-lo?",
        "tudo bem": "Tudo bem! Como posso ajudá-lo?",
        "como voce esta": "Estou funcionando perfeitamente! Como posso ajudá-lo?",
        "como você está": "Estou funcionando perfeitamente! Como posso ajudá-lo?",
        "qual seu nome": "Sou o MentorIA, seu assistente de IA. Como posso ajudá-lo?",
        "qual é seu nome": "Sou o MentorIA, seu assistente de IA. Como posso ajudá-lo?",
        "quem e voce": "Sou o MentorIA, seu assistente de IA. Como posso ajudá-lo?",
        "quem é você": "Sou o MentorIA, seu assistente de IA. Como posso ajudá-lo?",
        "obrigado": "De nada! Estou aqui para ajudar. Tem mais alguma dúvida?",
        "muito obrigado": "De nada! Estou aqui para ajudar. Tem mais alguma dúvida?",
        "obrigada": "De nada! Estou aqui para ajudar. Tem mais alguma dúvida?",
        "muito obrigada": "De nada! Estou aqui para ajudar. Tem mais alguma dúvida?",
        "valeu": "De nada! Estou aqui para ajudar. Tem mais alguma dúvida?",
        "brigado": "De nada! Estou aqui para ajudar. Tem mais alguma dúvida?",
        "brigada": "De nada! Estou aqui para ajudar. Tem mais alguma dúvida?",
        "tchau": "Até logo! Volte sempre que precisar de ajuda!",
        "adeus": "Até logo! Volte sempre que precisar de ajuda!",
        "até logo": "Até logo! Volte sempre que precisar de ajuda!",
        "até mais": "Até logo! Volte sempre que precisar de ajuda!",
        "bye": "Até logo! Volte sempre que precisar de ajuda!",
        "o que voce sabe": "Sou o MentorIA, seu assistente de IA. Posso ajudá-lo com informações sobre os documentos carregados nesta base de dados. Pergunte-me qualquer coisa!",
        "com oque pode me ajudar": "Sou o MentorIA, seu assistente de IA. Posso ajudá-lo a estudar diversos conteúdos! Selecione a base de dados adequada para seu estudo e vamos começar!",
        "como funciona": "Eu uso meu conhecimento baseado no conhecimento desta base de dados para responder suas dúvidas. É só perguntar!",
        "crie um teste de estudo": "Com certeza! Posso apresentar perguntas de múltipla escolha ou discursivas sobre o conteúdo desejado! Por onde quer começar? É só me dizer uma matéria, conteúdo ou tema!"
    }
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for comparison.
        - Remove accents
        - Convert to lowercase
        - Remove extra spaces
        - Remove punctuation
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Remove accents
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation and extra spaces
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def get_instant_response(question: str) -> Optional[str]:
        """
        Get instant response for a question if it matches a known pattern.
        Only exact matches are returned to avoid false positives with complex queries.
        
        Args:
            question: User's question
            
        Returns:
            Response text if found, None otherwise
        """
        normalized_question = InstantResponseService.normalize_text(question)
        
        # Exact match only
        if normalized_question in InstantResponseService.INSTANT_RESPONSES:
            response = InstantResponseService.INSTANT_RESPONSES[normalized_question]
            logger.info(f"Instant response matched: '{question}' -> '{response[:50]}...'")
            return response
        
        return None
