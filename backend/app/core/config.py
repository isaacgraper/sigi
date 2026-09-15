"""Application configuration, read from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings, with defaults that make a fresh clone run.

    The defaults are development values on purpose. A deployment that keeps any
    of them has not been configured.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    tz: str = "America/Sao_Paulo"
    database_url: str = "postgresql+psycopg://sigi:sigi@localhost:5432/sigi"
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Return the settings, read once per process.

    Cached because the environment does not change under a running process, and
    re-reading it per request would make configuration a hot path. Tests that
    change the environment call ``get_settings.cache_clear()``.
    """
    return Settings()
