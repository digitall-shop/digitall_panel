from functools import lru_cache
from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    # Core
    app_name: str = Field("VPN Panel", alias="APP_NAME")
    environment: str = Field("dev", alias="ENVIRONMENT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    # DB / Cache
    database_url: Optional[str] = Field(None, alias="DATABASE_URL")  # Optional for agents without DB
    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")
    # Auth
    secret_key: str = Field("devsecret", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_minutes: int = Field(60 * 24 * 30, alias="REFRESH_TOKEN_EXPIRE_MINUTES")
    jwt_alg: str = Field("HS256", alias="JWT_ALG")
    # Security
    admin_ip_allowlist: str = Field("127.0.0.1/32,::1/128", alias="ADMIN_IP_ALLOWLIST")
    # Metrics
    prometheus_multiproc_dir: Optional[str] = Field(None, alias="PROMETHEUS_MULTIPROC_DIR")
    # Node / Ingest
    sample_interval_seconds: int = Field(60, alias="SAMPLE_INTERVAL_SECONDS")
    # Scheduler
    scheduler_interval_seconds: int = Field(60, alias="SCHEDULER_INTERVAL_SECONDS")

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
