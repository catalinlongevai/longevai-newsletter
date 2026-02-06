from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "LongevAI API"
    env: str = "dev"
    python_version_required: str = "3.12"

    database_url: str = "postgresql+psycopg://longevai:longevai@localhost:5432/longevai"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_eager_mode: bool = False

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ncbi_api_key: str | None = None
    beehiiv_api_key: str | None = None
    beehiiv_publication_id: str | None = None

    allowed_fetch_hosts: str = ""
    api_auth_enabled: bool = True
    api_auth_token: str | None = None
    llm_enabled: bool = False
    beehiiv_enabled: bool = False
    observability_enabled: bool = True

    llm_timeout_seconds: int = 40
    llm_max_retries: int = 3
    ingest_http_timeout_seconds: int = 20
    idempotency_ttl_hours: int = 168
    source_run_retention_days: int = 30

    @property
    def allowed_fetch_host_list(self) -> list[str]:
        return [item.strip().lower() for item in self.allowed_fetch_hosts.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_feature_flags(self) -> "Settings":
        if self.api_auth_enabled and not self.api_auth_token and self.env not in {"test"}:
            raise ValueError("api_auth_token is required when api_auth_enabled=true")
        if self.beehiiv_enabled and (not self.beehiiv_api_key or not self.beehiiv_publication_id):
            raise ValueError(
                "beehiiv_api_key and beehiiv_publication_id are required when beehiiv_enabled=true"
            )
        if self.llm_enabled and (not self.openai_api_key and not self.anthropic_api_key):
            raise ValueError(
                "At least one provider key is required when llm_enabled=true"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
