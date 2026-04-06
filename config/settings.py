from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field
import os
import json
from typing import Optional, List, Dict, Any

class Settings(BaseSettings):

    # Project Configuration
    PROJECT_NAME: str = "Techstein RAG Portal"
    LOG_LEVEL: str
    
    # Directories
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_DIR: str = os.path.join(BASE_DIR, "logs", "api")
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    CACHE_DIR: str = os.path.join(BASE_DIR, "cache")

    # Relational Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432

    @property
    def POSTGRES_URL(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Vector Database
    QDRANT_HOST: str
    QDRANT_PORT: int = 6333

    @property
    def QDRANT_URL(self):
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # AI/LLM Provider API Keys
    OLLAMA_API_KEY: str = "ollama"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    HUGGINGFACE_TOKEN: str = ""

    # LLM Configuration
    LLM_PROVIDER: str = "ollama"  # ollama, openai, gemini
    LLM_MODEL: str = "llama3.1:8b"

    # Embedding & Reranking Models Configuration
    EMBEDDING_MODEL_ID: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    RERANKER_MODEL_ID: str = "BAAI/bge-reranker-v2-m3"
    
    # RAG Parameters
    K_RETRIEVAL: int = 10
    TOP_K: int = 5
    THRESHOLD: float = 0.0
    QUERY_EXPANSION_COUNT: int = 3
    
    # System User
    SYSTEM_USER_EMAIL: str
    SYSTEM_USER_PASSWORD: str

    # JWT Configuration
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email Configuration
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # Rate Limiting Configuration (simples, em memória)
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_MINUTES: int = 5
    LOGIN_BLOCK_MINUTES: int = 10

    # Development Configuration
    DEV_MODE: bool = True

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Retorna os modelos LLM disponíveis para seleção.
        O modelo padrão (LLM_MODEL + LLM_PROVIDER) é sempre incluído.
        Configure modelos adicionais editando a lista abaixo.
        """
        additional_models = [
            {
                "model": "llama3.2:3b",
                "provider": "ollama",
                "description": "Llama 3.2 3B model via Ollama (local)"
            },
            {
                "model": "llama3.1:8b",
                "provider": "ollama",
                "description": "Llama 3.1 8B model via Ollama (local)"
            },
        ]
        
        default_model = {
            "model": self.LLM_MODEL,
            "provider": self.LLM_PROVIDER,
            "description": f"Default model ({self.LLM_MODEL} via {self.LLM_PROVIDER})"
        }
        
        models = [default_model]
        seen = {(self.LLM_MODEL, self.LLM_PROVIDER)}
        
        for model in additional_models:
            key = (model["model"], model["provider"])
            if key not in seen:
                models.append(model)
                seen.add(key)
        
        return models

settings = Settings()