"""Environment-backed settings."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The public API rejects anything above this, even if the env value is higher.
MAX_TOP_K_CAP = 20

INSECURE_JWT_SECRETS = frozenset(
    {
        "local-dev-secret-change-before-exposing",
        "change-me",
        "secret",
        "changeme",
    }
)


class Settings(BaseSettings):
    """Runtime configuration. Values come from the environment or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg2://semantic:semantic@localhost:5433/semantic_search"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = Field(default=384, gt=0)
    max_upload_size_bytes: int = Field(default=50 * 1024 * 1024, gt=0)
    chunk_size: int = Field(default=500, ge=1)
    chunk_overlap: int = Field(default=50, ge=0)
    default_top_k: int = Field(default=5, ge=1)
    max_top_k: int = Field(default=MAX_TOP_K_CAP, ge=1, le=MAX_TOP_K_CAP)
    init_db_on_startup: bool = True
    jwt_secret: str = Field(default="local-dev-secret-change-before-exposing", min_length=16)
    jwt_expire_minutes: int = Field(default=60 * 24, ge=1)
    allow_insecure_jwt: bool = False
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    category_min_score: float = Field(default=0.35, ge=0.0, le=1.0)
    min_search_score: float = Field(default=0.25, ge=0.0, le=1.0)
    max_concurrent_upload_jobs: int = Field(default=2, ge=1, le=16)
    max_pdf_pages: int = Field(default=200, ge=1)
    max_extracted_text_chars: int = Field(default=2_000_000, ge=10_000)
    max_chunks_per_document: int = Field(default=2_000, ge=1)
    auth_rate_limit_per_minute: int = Field(default=30, ge=1)
    upload_rate_limit_per_minute: int = Field(default=20, ge=1)
    search_rate_limit_per_minute: int = Field(default=60, ge=1)
    recover_stuck_processing_on_startup: bool = True

    @model_validator(mode="after")
    def check_ranges(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.default_top_k > self.max_top_k:
            raise ValueError("DEFAULT_TOP_K must be less than or equal to MAX_TOP_K")
        if not self.allow_insecure_jwt and self.jwt_secret.strip() in INSECURE_JWT_SECRETS:
            raise ValueError(
                "JWT_SECRET is a known insecure default. Set a strong secret or "
                "ALLOW_INSECURE_JWT=true for local development only."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()