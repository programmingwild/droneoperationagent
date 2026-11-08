"""Application configuration via pydantic-settings. All secrets come from .env / environment."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # --- LLM provider ---
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    # auto = use openai when a key is present, else the explicit offline fallback
    llm_provider: str = "auto"  # auto | openai | local
    embedding_provider: str = "auto"  # auto | openai | local

    # --- Vector store ---
    vector_backend: str = "auto"  # auto | pinecone | local
    pinecone_api_key: str | None = None
    pinecone_index: str = "droneops"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    local_vector_store_path: str = str(REPO_ROOT / "data" / "vector_store.json")
    rag_top_k: int = 4
    rag_confidence_threshold: float = 0.33

    # --- Storage (tickets / approvals / runs) ---
    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'droneops.db'}"

    # --- LangSmith tracing (env-gated) ---
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "drone-ops-agent"

    # --- NOTAM / airspace proxy ---
    aviationweather_base_url: str = "https://aviationweather.gov/api/data"
    notam_cache_ttl_s: int = 900
    http_timeout_s: float = 8.0

    # --- App ---
    log_level: str = "INFO"
    app_env: str = "development"
    # where flight-log CSVs may live for the /logs endpoint
    flight_logs_dir: str = str(REPO_ROOT / "data" / "sample_logs")

    @field_validator("llm_provider", "embedding_provider", "vector_backend")
    @classmethod
    def _lower(cls, v: str) -> str:
        return (v or "auto").lower().strip()

    @property
    def data_dir(self) -> Path:
        p = REPO_ROOT / "data"
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
