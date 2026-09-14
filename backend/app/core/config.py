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

    # ── Sessão (RNF03, ADR-0010) ────────────────────────────────────────────
    # PEM, por configuração e nunca no repositório. Vazias em `development`
    # fazem o app gerar um par efêmero no arranque; fora de `development` isso
    # é erro de inicialização, porque um par efêmero em produção invalida toda
    # sessão a cada restart e ninguém liga os dois fatos.
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

    # ── Credenciais locais (ADR-0010) ───────────────────────────────────────
    # Desligável: o default honesto de produção é `False`, com OIDC como
    # caminho primário. Ligado aqui para que um clone novo funcione.
    local_login_enabled: bool = True
    dominios_institucionais: list[str] = ["sc.gov.br"]
    bcrypt_cost: int = 12
    senha_tamanho_minimo: int = 12

    # ── OIDC institucional (ADR-0010, AC-0001-19..22) ───────────────────────
    # Entra ID. A entidade ainda não entregou tenant, client e redirect (OQ-09),
    # então os defaults vazios desligam o caminho e os testes injetam os seus.
    oidc_enabled: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:3000/auth/callback"
    # Claim de grupo que o provedor assere. Registrada na auditoria do login e
    # nunca consultada por decisão de autorização (AC-0001-22).
    oidc_claim_grupo: str = "groups"
    # Janela entre iniciar o login e voltar do provedor.
    oidc_estado_ttl_minutos: int = 10

    # ── Bloqueio por tentativas (AC-0001-03) ────────────────────────────────
    max_tentativas_login: int = 5
    janela_tentativas_minutos: int = 15
    bloqueio_minutos: int = 15

    # ── Convites e redefinições (AC-0001-11, -25, -31) ──────────────────────
    # Base do link que o gestor copia e entrega (AC-0001-10, v0.6). O backend
    # monta o link porque é ele que conhece o token — que existe por um instante
    # só, na resposta da criação, e depois some: o banco guarda apenas o HMAC.
    url_base_frontend: str = "http://localhost:3000"
    convite_ttl_horas: int = 72
    # Uma hora contra as 72 do convite: convite espera alguém arrumar tempo de
    # entrar, redefinição é pedida por quem está na frente da tela.
    redefinicao_ttl_horas: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()
