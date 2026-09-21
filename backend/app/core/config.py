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

    # ── Session (RNF03, ADR-0010) ───────────────────────────────────────────
    # PEM, from configuration and never from the repository. Empty in
    # `development` makes the app generate an ephemeral pair at startup; outside
    # `development` that is a startup error, because an ephemeral pair in
    # production invalidates every session on each restart and nobody connects
    # those two facts.
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_issuer: str = "sigi"
    access_token_ttl_minutos: int = 15
    refresh_token_ttl_dias: int = 7
    # AC-0001-01 requires the refresh cookie to be Secure. Configurable only so
    # that a developer serving over plain http can flip it; leaving it False in
    # production ships the refresh token over the wire in clear.
    cookie_secure: bool = True
    cookie_refresh_nome: str = "sigi_refresh"

    # ── Institutional OIDC (ADR-0010, AC-0001-19 to -22) ────────────────────
    # Entra ID. The entity has not yet handed over tenant, client and redirect
    # (OQ-09), so the empty defaults leave the path off and the tests inject
    # their own.
    oidc_enabled: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:3000/auth/callback"
    # The group claim the provider asserts. Recorded in the login's audit row
    # and never consulted by an authorisation decision (AC-0001-22).
    oidc_claim_grupo: str = "groups"
    # The window between starting a login and returning from the provider.
    oidc_estado_ttl_minutos: int = 10

    # ── Local credentials (ADR-0010) ────────────────────────────────────────
    # Switchable: the honest production default is `False`, with OIDC as the
    # primary path. On here so that a fresh clone runs.
    local_login_enabled: bool = True
    dominios_institucionais: list[str] = ["sc.gov.br"]
    bcrypt_cost: int = 12
    senha_tamanho_minimo: int = 12

    # ── Per-address lockout (AC-0001-03) ────────────────────────────────────
    max_tentativas_login: int = 5
    # ── Per-source rate limiting (AC-0001-33, ADR-0012) ────────────────────
    # Configuration rather than constants, so the entity can tune these against
    # its real traffic without a deploy (ADR-0012 §3).
    rate_limit_janela_segundos: int = 60
    # **Every** route under the throttled prefixes needs an entry here. There is
    # deliberately no default to fall back on: a default would make
    # `verify_ceilings` vacuous, since every route would always "have" a
    # ceiling, and AC-0001-33's last clause asks for the opposite. Adding a
    # route under those prefixes breaks the build until its ceiling is chosen,
    # which is the same bargain `verify_coverage` makes for authorisation.
    rate_limit_tetos: dict[str, int] = {
        "/api/v1/auth/login": 20,
        "/api/v1/auth/refresh": 60,
        "/api/v1/auth/logout": 60,
        "/api/v1/auth/me": 120,
        "/api/v1/auth/oidc/authorize": 30,
        "/api/v1/auth/oidc/callback": 30,
        "/api/v1/auth/redefinicoes/confirmar": 10,
        "/api/v1/convites/ativar": 10,
    }
    # A higher ceiling, never an exemption (ADR-0012 §4). Whole unidades sit
    # behind one NAT address, so an internet-tuned ceiling locks out a building
    # on its first busy morning — while an exemption would leave an attacker who
    # reached the internal network facing no limit at all.
    rate_limit_faixas_institucionais: list[str] = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]
    rate_limit_teto_institucional: int = 600

    janela_tentativas_minutos: int = 15
    bloqueio_minutos: int = 15

    # ── Invitations and resets (AC-0001-11, -25, -31) ───────────────────────
    # Where an activation or reset link points. The token travels as a query
    # parameter on the frontend route, which then posts it in a request body:
    # a link has to be openable, but our API never takes it in a path.
    url_base_frontend: str = "http://localhost:3000"
    convite_ttl_horas: int = 72
    # One hour against the invitation's 72: an invitation waits for somebody to
    # find the time, a reset is asked for by someone sitting at the screen.
    redefinicao_ttl_horas: int = 1


@lru_cache
def get_settings() -> Settings:
    """Return the settings, read once per process.

    Cached because the environment does not change under a running process, and
    re-reading it per request would make configuration a hot path. Tests that
    change the environment call ``get_settings.cache_clear()``.
    """
    return Settings()
