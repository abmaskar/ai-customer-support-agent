"""Project settings – load secrets from .env only."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    # App
    app_name: str = "AI Customer Support Agent"
    secret_key: SecretStr = SecretStr("change-me-in-production")
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Database
    database_url: str = "postgresql+psycopg2://support:support@localhost:5432/support_agent"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "support_docs"

    # LLM
    default_provider: str = "ollama"  # ollama | openai
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    temperature: float = 0.2
    max_tokens: int = 1024

    # Metrics thresholds
    eval_groundedness_target: float = 0.80
    fallback_rate_target: float = 0.20
    p95_latency_target_ms: float = 3000.0

    @property
    def cors_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
