from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = ""  # local dev only; Cloud Run uses CLOUD_SQL_INSTANCE + DB_* vars
    gcs_bucket_raw: str = "radar-raw"
    pubsub_project_id: str
    pubsub_topic_collect: str = "collect-trigger"
    pubsub_topic_events: str = "property-events"
    telegram_bot_token: str
    firebase_credentials_json: str  # JSON string da service account
    caixa_request_delay_ms: int = 1000
    caixa_max_retries: int = 3
    alert_max_retries: int = 3
    score_discount_max_points: int = 60
    score_occupancy_bonus: int = 40
    telegram_token_ttl_seconds: int = 900
    api_cors_origins: str = "https://radarimovel.com.br"
    redis_url: str = "redis://localhost:6379"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
