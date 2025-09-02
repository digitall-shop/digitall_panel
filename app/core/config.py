from functools import lru_cache
from pydantic import BaseSettings
import secrets

class Settings(BaseSettings):
    app_name: str = "HighScaleVPNPanel"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = secrets.token_urlsafe(32)
    access_token_expire_minutes: int = 60 * 24
    sqlalchemy_database_url: str = "sqlite+aiosqlite:///./app.db"  # override with postgres for prod
    redis_url: str = "redis://localhost:6379/0"
    wireguard_bin: str = "wg"
    wireguard_base_interface: str = "wg0"
    max_users: int = 100_000
    # Initial superuser bootstrap (optional)
    first_superuser: str | None = "admin"
    first_superuser_password: str | None = "admin123"

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
