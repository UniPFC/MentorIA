from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import os

class Settings(BaseSettings):

    # Project Configuration
    PROJECT_NAME: str = "Techstein RAG Portal"
    LOG_LEVEL: str
    
    # Directories
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_DIR: str = os.path.join(BASE_DIR, "logs", "api")

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

    # Embedding & Reranking Models
    EMBEDDING_MODEL_ID: str = "mixedbread-ai/mxbai-embed-large-v1"
    RERANKER_MODEL_ID: str = "BAAI/bge-reranker-base"
    
    # RAG Parameters
    K_RETRIEVAL: int = 10
    TOP_K: int = 5
    THRESHOLD: float = 0.3

    # JWT Configuration
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()