from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field
import os
from typing import Optional

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

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()