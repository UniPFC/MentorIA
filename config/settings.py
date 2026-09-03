import os
from typing import Any

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Project Configuration
    PROJECT_NAME: str = "MentorIA"
    TERMS_VERSION: str = "1.1"
    LOG_LEVEL: str

    # Directories
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_DIR: str = os.path.join(BASE_DIR, "logs", "api")
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    CACHE_DIR: str = os.path.join(BASE_DIR, "cache")
    PROMPTS_DIR: str = os.path.join(BASE_DIR, "src", "rag", "prompts")

    # Relational Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432

    @property
    def POSTGRES_URL(self):
        # Alterado temporariamente para prefer para testar local sem SSL
        ssl_mode = "prefer"
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?sslmode={ssl_mode}"

    # Vector Database
    QDRANT_HOST: str
    QDRANT_PORT: int = 6333
    QDRANT_STORAGE_DIR: str = "/qdrant/storage"

    @property
    def QDRANT_URL(self):
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # AI/LLM Provider API Keys
    OLLAMA_API_KEY: str = "ollama"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    HUGGINGFACE_TOKEN: str = ""

    @property
    def HF_TOKEN(self):
        return self.HUGGINGFACE_TOKEN

    # LLM Configuration
    LLM_PROVIDER: str = "ollama"  # ollama, openai, gemini
    LLM_MODEL: str = "llama3.1:8b"

    # Embedding & Reranking Models Configuration
    EMBEDDING_PROVIDER: str
    EMBEDDING_MODEL_ID: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_REMOTE_MODEL: str = "text-embedding-3-small"
    EMBEDDING_REMOTE_PROVIDER: str = "openai"
    RERANKER_MODEL_ID: str = "cross-encoder/mmarco-mMiniLMv2-L6-H384-v1"

    # Speech-to-Text Configuration
    STT_ENABLED: bool = False
    STT_MODEL: str = "small"  # tiny, base, small, medium, large
    STT_COMPUTE_TYPE: str = "int8"  # int8, int16, float16, float32
    STT_TIMEOUT: int = 30  # seconds to wait for memory before failing

    # RAG Parameters
    K_RETRIEVAL: int = 10
    TOP_K: int = 5
    THRESHOLD: float = 0.0
    QUERY_EXPANSION_COUNT: int = 3

    # Admin Configuration
    SYSTEM_USER_EMAIL: str
    SYSTEM_USER_PASSWORD: str
    ADMIN_SLUG: str

    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Password Security Configuration
    PASSWORD_PEPPER: str

    # Encryption Configuration
    ENCRYPTION_SALT: str

    # Email Configuration
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    # Services
    AI_WORKER_URL: str = "http://ai_worker:8001"
    INTERNAL_API_KEY: str = "mentoria-internal-secret-token-2026"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # Rate Limiting Configuration (simples, em memória)
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_MINUTES: int = 5
    LOGIN_BLOCK_MINUTES: int = 10

    # Token Budget Configuration per User Level
    TOKEN_BUDGET_LEVEL_01: int = 10000  # Free
    TOKEN_BUDGET_LEVEL_02: int = 1000000  # Lite
    TOKEN_BUDGET_LEVEL_03: int = 8000000  # Plus
    TOKEN_BUDGET_LEVEL_04: int = 18000000  # Max
    TOKEN_BUDGET_MINIMUM_RESERVE: int = 200

    # Cost Tier Configuration
    COST_TIER_MIN_MULTIPLIER: float = 0.1  # Minimum multiplier for cost tier 0
    COST_TIER_MAX_MULTIPLIER: float = 3.0  # Maximum multiplier for cost tier 9

    # Pagar.me Configuration
    PAGARME_API_KEY: str = ""
    PAGARME_WEBHOOK_SECRET: str = ""
    PAGARME_API_URL: str = "https://api.pagar.me/core/v5"

    # Pagar.me Plan IDs (one per level, configure in .env)
    PAGARME_PLAN_LEVEL_02: str = ""  # Plan ID for LEVEL_02 subscription
    PAGARME_PLAN_LEVEL_03: str = ""  # Plan ID for LEVEL_03 subscription
    PAGARME_PLAN_LEVEL_04: str = ""  # Plan ID for LEVEL_04 subscription

    # Pagar.me Refill item price ID
    PAGARME_REFILL_ITEM_ID: str = ""  # One-time charge item for token refill

    # Development Configuration
    DEV_MODE: bool = False
    SKIP_PAYMENT: bool = False  # Skip payment processing (for testing without Pagar.me)

    # Security & Behavior Flags
    SECURE_COOKIES: bool = True
    AUTO_RUN_SEEDER: bool = True
    ENABLE_API_DOCS: bool = False

    # HTTPS Configuration
    FORCE_HTTPS: bool = True

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_available_models(self) -> list[dict[str, Any]]:
        """
        Retorna os modelos LLM disponíveis para seleção.
        O modelo padrão (LLM_MODEL + LLM_PROVIDER) é sempre incluído.
        Configure modelos adicionais editando a lista abaixo.

        input_token_multiplier: Multiplicador de custo para tokens de entrada
        output_token_multiplier: Multiplicador de custo para tokens de saída
        - 1.0 = custo base
        - >1.0 = modelo mais caro (deduz mais tokens do budget)
        - <1.0 = modelo mais barato (deduz menos tokens do budget)
        minimum_level: nível mínimo necessário para selecionar o modelo
        """
        additional_models = [
            {
                "model": "gpt-5-nano",
                "provider": "openai",
                "description": "Modelo rápido e econômico para perguntas do dia a dia",
                "input_token_multiplier": 0.5,
                "output_token_multiplier": 0.5,
                "minimum_level": "LEVEL_01",
            },
            {
                "model": "gpt-4o-mini",
                "provider": "openai",
                "description": "Modelo equilibrado para estudos e respostas rápidas",
                "input_token_multiplier": 1.0,
                "output_token_multiplier": 1.0,
                "minimum_level": "LEVEL_01",
            },
            {
                "model": "gpt-5.6-luna",
                "provider": "openai",
                "description": "Modelo GPT-5.6 eficiente para respostas mais completas",
                "input_token_multiplier": 2.0,
                "output_token_multiplier": 2.0,
                "minimum_level": "LEVEL_03",
            },
            {
                "model": "gpt-4.1-mini",
                "provider": "openai",
                "description": "Modelo avançado para instruções mais detalhadas",
                "input_token_multiplier": 3.0,
                "output_token_multiplier": 3.0,
                "minimum_level": "LEVEL_03",
            },
        ]

        default_model = next(
            (
                model.copy()
                for model in additional_models
                if model["model"] == self.LLM_MODEL
                and model["provider"] == self.LLM_PROVIDER
            ),
            {
                "model": self.LLM_MODEL,
                "provider": self.LLM_PROVIDER,
                "description": f"Default model ({self.LLM_MODEL} via {self.LLM_PROVIDER})",
                "input_token_multiplier": 1.0,
                "output_token_multiplier": 1.0,
                "minimum_level": "LEVEL_01",
            },
        )

        models = [default_model]
        seen: set[tuple[str, str]] = {(str(self.LLM_MODEL), str(self.LLM_PROVIDER))}

        for model in additional_models:
            key = (str(model["model"]), str(model["provider"]))
            if key not in seen:
                models.append(model)
                seen.add(key)

        return models


settings = Settings()
