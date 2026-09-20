"""Domain exceptions.

Services raise these; `app/api/erros.py` maps them to the envelope in
`api-conventions.md`. `CLAUDE.md` forbids raising `HTTPException` below the API
layer, which is what keeps the domain rules testable without a request.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base for anything a caller did wrong.

    `code` is stable and machine-readable; `message` is pt-BR, addressed to a
    servidor, and says what to do next. `fields` drives inline field errors — a
    single generic "dados inválidos" defeats the whole point, which is mitigating
    the transcription errors that motivated the project.
    """

    code: str = "DOMAIN_ERROR"
    http: int = 422

    def __init__(
        self,
        message: str,
        *,
        fields: dict[str, str] | None = None,
        retry_after: int | None = None,
    ) -> None:
        """Build the error with its pt-BR message, field detail and retry hint."""
        super().__init__(message)
        self.mensagem = message
        self.campos = fields or {}
        # Seconds for a `Retry-After` header. A 429 whose only statement of
        # "when" is inside a pt-BR sentence is a 429 no client can obey.
        self.retry_after = retry_after


class InvalidCredentials(DomainError):
    """Wrong password, unknown e-mail, or an address off the allowlist.

    One class for all three on purpose: AC-0001-02 requires the three responses
    to be byte-identical, and having separate classes is how they drift apart.
    """

    code = "INVALID_CREDENTIALS"
    http = 401

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("E-mail ou senha inválidos.")


class InactiveUser(DomainError):
    """The credential is right and the account is not ativo."""

    code = "USUARIO_INATIVO"
    http = 401

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("Esta conta não está ativa. Procure o gestor da sua unidade.")


class InvalidRefresh(DomainError):
    """The refresh token is unknown, expired, or already rotated."""

    code = "INVALID_REFRESH"
    http = 401

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("Sua sessão não é mais válida. Entre novamente.")


class RouteUnavailable(DomainError):
    """A mechanism switched off by configuration (AC-0001-24).

    404 rather than 403: a mechanism that is off should be indistinguishable
    from one that was never built.
    """

    code = "NOT_FOUND"
    http = 404

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("Recurso não encontrado.")


class AttemptsExceeded(DomainError):
    """The address is locked after repeated failures (AC-0001-03).

    429 rather than 401: the caller is not being told their credential is
    wrong — this attempt was never evaluated.
    """

    code = "ATTEMPTS_EXCEEDED"
    http = 429

    def __init__(self, *, minutes: int) -> None:
        """Build the error, carrying the wait in seconds for `Retry-After`."""
        super().__init__(
            f"Muitas tentativas. Tente novamente em {minutes} minutos.",
            retry_after=minutes * 60,
        )


class InvalidState(DomainError):
    """The OIDC callback carries a state that was never issued, or has expired."""

    code = "INVALID_STATE"
    http = 401

    def __init__(self) -> None:
        """Build the error. It says nothing about which of the two it was."""
        super().__init__("A tentativa de entrada expirou. Comece novamente.")


class InvalidAssertion(DomainError):
    """The provider's identity token did not verify (AC-0001-20)."""

    code = "INVALID_ASSERTION"
    http = 401

    def __init__(self) -> None:
        """Build the error, naming no detail of why verification failed."""
        super().__init__("Não foi possível validar a resposta do provedor.")


class UnprovisionedUsuario(DomainError):
    """The assertion verified, and no usuario matches it (AC-0001-21).

    403 and not 404: the caller authenticated against the tenant, so they exist
    as a person. What they lack is an account here, and saying so is what tells
    them to ask the gestor rather than retry.
    """

    code = "USUARIO_NAO_PROVISIONADO"
    http = 403

    def __init__(self) -> None:
        """Build the error, pointing the caller at the gestor who can fix it."""
        super().__init__("Seu acesso ainda não foi liberado. Procure o gestor da sua unidade.")


class UnauthorizedPerfil(DomainError):
    """Authenticated, and the perfil does not permit it (RN04, A01).

    403 rather than 404 on purpose: the caller is a known servidor of the
    entity, and hiding that the action exists would only make them ask a
    colleague to try it too.
    """

    code = "PERFIL_NAO_AUTORIZADO"
    http = 403

    def __init__(self) -> None:
        """Build the error. It carries no detail, because the perfil is the reason."""
        super().__init__("Seu perfil não permite esta ação.")
