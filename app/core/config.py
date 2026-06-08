from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = ""  # local dev only; Cloud Run uses CLOUD_SQL_INSTANCE + DB_* vars
    gcs_bucket_raw: str = "radar-raw"
    pubsub_project_id: str = ""
    pubsub_topic_collect: str = "collect-trigger"
    pubsub_topic_events: str = "property-events"
    pubsub_topic_editais: str = "edital-events"
    pubsub_sub_editais: str = "edital-events-sub"
    gcs_bucket_docs: str = "radar-imovel-docs"
    vertex_location: str = "us-central1"
    gemini_model: str = "gemini-2.0-flash"
    gemini_fallback_model: str = ""
    gemini_confidence_floor: float = 0.60
    edital_confidence_threshold: float = 0.75
    edital_download_timeout_s: int = 30
    edital_max_retries: int = 3
    edital_batch_size: int = 50
    telegram_bot_token: str = ""
    firebase_credentials_json: str = ""
    caixa_request_delay_ms: int = 1000
    caixa_max_retries: int = 3
    alert_max_retries: int = 3
    score_discount_max_points: int = 60
    score_occupancy_bonus: int = 40
    score_discount_enriched_max: int = 45
    score_occupancy_enriched_max: int = 20
    score_payment_max: int = 10
    score_proximity_max: int = 5
    score_debt_penalty_max: int = 30
    score_risk_flag_penalty: int = 7
    score_risk_flag_penalty_max: int = 20
    score_onus_penalty: int = 15
    telegram_token_ttl_seconds: int = 900
    api_cors_origins: str = "https://radarimovel.com.br,https://radar-imovel-frontend-ebtyy3lmba-uc.a.run.app,http://localhost:3000"
    redis_url: str = "redis://localhost:6379"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
