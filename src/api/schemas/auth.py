from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID
from zxcvbn import zxcvbn


# Mapeamento de traduções para dicas e avisos do zxcvbn
ZXCVBN_TRANSLATIONS = {
    # Sugestões gerais
    "Add another word or two": "Adicione mais uma ou duas palavras",
    "Add another word or two. Uncommon words are better.": "Adicione mais uma ou duas palavras. Palavras incomuns são melhores.",
    "Uncommon words are better": "Palavras incomuns são melhores",
    "Avoid repeated words and characters": "Evite palavras e caracteres repetidos",
    "Avoid sequences": "Evite sequências (como 'abc', '123')",
    "Avoid recent years": "Evite anos recentes",
    "Avoid years that are associated with you": "Evite anos associados a você",
    "Avoid dates and years that are associated with you.": "Evite datas e anos associados a você",
    "Avoid user-related words": "Evite palavras relacionadas ao usuário",
    "No need for symbols, digits, or uppercase letters": "Não é necessário usar símbolos, dígitos ou letras maiúsculas",
    "No need for symbols, digits, or uppercase letters.": "Não é necessário usar símbolos, dígitos ou letras maiúsculas.",
    "Use a few words, avoid common phrases": "Use algumas palavras, evite frases comuns",
    "Use a few words, avoid common phrases.": "Use algumas palavras, evite frases comuns.",
    "Use a longer keyboard pattern with more turns.": "Use um padrão de teclado mais longo com mais voltas.",
    "All-uppercase is almost as easy to guess as all-lowercase": "Tudo em maiúsculas é quase tão fácil de adivinhar quanto tudo em minúsculas",
    "All-uppercase is almost as easy to guess as all-lowercase.": "Tudo em maiúsculas é quase tão fácil de adivinhar quanto tudo em minúsculas.",
    "Capitalization doesn't help very much": "Capitalização não ajuda muito",
    "Capitalization doesn't help very much.": "Capitalização não ajuda muito.",
    "Reversed words aren't much harder to guess": "Palavras invertidas não são muito mais difíceis de adivinhar",
    "Reversed words aren't much harder to guess.": "Palavras invertidas não são muito mais difíceis de adivinhar.",
    "Predictable substitutions like '@' instead of 'a' don't help very much": "Substituições previsíveis como '@' em vez de 'a' não ajudam muito",
    "Predictable substitutions like '@' instead of 'a' don't help very much.": "Substituições previsíveis como '@' em vez de 'a' não ajudam muito.",
    "Straight rows of keys are easy to guess.": "Linhas retas de teclas são fáceis de adivinhar.",
    "Short keyboard patterns are easy to guess.": "Padrões curtos de teclado são fáceis de adivinhar.",
    "Repeats like \"aaa\" are easy to guess.": "Repetições como 'aaa' são fáceis de adivinhar.",
    "Repeats like \"abcabcabc\" are only slightly harder to guess than \"abc\".": "Repetições como 'abcabcabc' são apenas um pouco mais difíceis de adivinhar que 'abc'.",
    "Sequences like \"abc\" or \"6543\" are easy to guess.": "Sequências como 'abc' ou '6543' são fáceis de adivinhar.",
    "Recent years are easy to guess.": "Anos recentes são fáceis de adivinhar.",
    "Dates are often easy to guess.": "Datas são frequentemente fáceis de adivinhar.",
    "This is a top-10 common password.": "Esta é uma das 10 senhas mais comuns.",
    "This is a top-100 common password.": "Esta é uma das 100 senhas mais comuns.",
    "This is a very common password.": "Esta é uma senha muito comum.",
    "This is similar to a commonly used password.": "Esta é semelhante a uma senha comumente usada.",
    "A word by itself is easy to guess.": "Uma palavra por si só é fácil de adivinhar.",
    "Names and surnames by themselves are easy to guess.": "Nomes e sobrenomes por si só são fáceis de adivinhar.",
    "Common names and surnames are easy to guess.": "Nomes e sobrenomes comuns são fáceis de adivinhar.",
}


def translate_zxcvbn_suggestion(suggestion: str) -> str:
    """Traduz sugestões do zxcvbn para português brasileiro"""
    return ZXCVBN_TRANSLATIONS.get(suggestion, suggestion)


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário")
    email: EmailStr = Field(..., description="Email válido")
    password: str = Field(..., min_length=8, max_length=100, description="Senha (mínimo 8 caracteres, força média ou superior)")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Valida username e bloqueia nomes reservados do sistema"""
        if v.lower() == 'mentoria':
            raise ValueError('O nome de usuário "MentorIA" é reservado para o sistema e não pode ser usado.')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Valida força da senha usando zxcvbn (score mínimo 2 = força média)"""
        if len(v.encode('utf-8')) > 1000:
            raise ValueError('Senha muito longa. Máximo 1000 bytes.')
        
        # Avaliar força da senha
        resultado = zxcvbn(v)
        score = resultado.get('score', 0)  # 0-4
        
        # Score 2+ = força média ou superior
        if score < 2:
            feedback = resultado.get('feedback', {})
            warning = feedback.get('warning', '')
            sugestoes = feedback.get('suggestions', [])
            
            # Construir mensagem com aviso + sugestões
            mensagem = "Senha fraca."
            
            # Adicionar aviso se existir
            if warning:
                warning_traduzido = translate_zxcvbn_suggestion(warning)
                mensagem += f" {warning_traduzido}"
            
            # Adicionar sugestões
            if sugestoes:
                sugestoes_traduzidas = [translate_zxcvbn_suggestion(s) for s in sugestoes[:2]]
                mensagem += " Dicas: " + "; ".join(sugestoes_traduzidas)
            else:
                mensagem += " Use uma combinação de maiúsculas, minúsculas, números e símbolos."
            
            raise ValueError(mensagem)
        
        return v


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Email do usuário")
    password: str = Field(..., description="Senha")
    
    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v):
        """Valida se a senha não excede limites seguros para processamento"""
        if len(v.encode('utf-8')) > 1000:  # Limite seguro para processamento
            raise ValueError('Senha muito longa. Máximo 1000 bytes.')
        return v


class Token(BaseModel):
    access_token: str = Field(..., description="Token JWT de acesso")
    refresh_token: str = Field(..., description="Token JWT de atualização")
    token_type: str = Field(default="bearer", description="Tipo do token")
    expires_in: int = Field(..., description="Tempo de expiração em segundos")


class TokenRefresh(BaseModel):
    refresh_token: str = Field(..., description="Token de atualização")


class UserResponse(BaseModel):
    """Schema for User response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    username: str
    email: str
    created_at: datetime


class LogoutResponse(BaseModel):
    message: str = Field(default="Logout realizado com sucesso")
    success: bool = Field(default=True)




class TokenVerifyResponse(BaseModel):
    valid: bool
    user_id: UUID
    username: str


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="Email do usuário para reset de senha")


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., description="Token de reset recebido por email")
    new_password: str = Field(..., min_length=8, max_length=100, description="Nova senha (mínimo 8 caracteres, força média ou superior)")
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Valida força da senha usando zxcvbn (score mínimo 2 = força média)"""
        if len(v.encode('utf-8')) > 1000:
            raise ValueError('Senha muito longa. Máximo 1000 bytes.')
        
        # Avaliar força da senha
        resultado = zxcvbn(v)
        score = resultado.get('score', 0)  # 0-4
        
        # Score 2+ = força média ou superior
        if score < 2:
            feedback = resultado.get('feedback', {})
            warning = feedback.get('warning', '')
            sugestoes = feedback.get('suggestions', [])
            
            # Construir mensagem com aviso + sugestões
            mensagem = "Senha fraca."
            
            # Adicionar aviso se existir
            if warning:
                warning_traduzido = translate_zxcvbn_suggestion(warning)
                mensagem += f" {warning_traduzido}"
            
            # Adicionar sugestões
            if sugestoes:
                sugestoes_traduzidas = [translate_zxcvbn_suggestion(s) for s in sugestoes[:2]]
                mensagem += " Dicas: " + "; ".join(sugestoes_traduzidas)
            else:
                mensagem += " Use uma combinação de maiúsculas, minúsculas, números e símbolos."
            
            raise ValueError(mensagem)
        
        return v
