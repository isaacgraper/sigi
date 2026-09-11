from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    tz: str = "America/Sao_Paulo"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Two roles, and they are not interchangeable. ADR-0004 enforces the
    # append-only audit trail with REVOKE UPDATE, DELETE plus a trigger, and an
    # owner can undo both — so the application must not connect as the owner.
    # `database_url` is the restricted role the app serves requests with;
    # `database_url_admin` runs Alembic and nothing else.
    database_url: str = "postgresql+psycopg://sigi_app:sigi_app@localhost:5432/sigi"
    database_url_admin: str = "postgresql+psycopg://sigi:sigi@localhost:5432/sigi"

    # The migration grants table privileges to this role and refuses to run if
    # it does not exist. Configurable so tests can provision their own.
    db_app_role: str = "sigi_app"

    # Keys `tentativa_login.email_hmac`, `limite_taxa.chave` and the audit
    # rows that record an address without storing it. **Rotating this is a
    # one-way decision**: it breaks lockout continuity and de-correlates every
    # historical audit row for a given address. The default exists so tests and
    # a fresh clone run; a deployment that keeps it has no pepper at all.
    hmac_pepper: str = "troque-este-valor-em-producao"


@lru_cache
def get_settings() -> Settings:
    return Settings()
