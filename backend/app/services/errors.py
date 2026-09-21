"""Domain exceptions.

Services raise these; `app/api/errors.py` maps them to the envelope in
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


class InviteAlreadyUsed(DomainError):
    """The grant was already redeemed, or never existed (AC-0001-25)."""

    code = "INVITE_ALREADY_USED"
    http = 409

    def __init__(self) -> None:
        """Build the error, which does not distinguish spent from unknown."""
        super().__init__("Este convite já foi utilizado. Peça um novo ao gestor.")


class InviteExpired(DomainError):
    """The grant timed out, or a newer one superseded it (AC-0001-25)."""

    code = "INVITE_EXPIRED"
    http = 409

    def __init__(self) -> None:
        """Build the error, pointing at the gestor who can issue another."""
        super().__init__("Este convite expirou. Peça um novo ao gestor.")


class WeakPassword(DomainError):
    """The chosen password is shorter than the policy allows (AC-0001-26)."""

    code = "WEAK_PASSWORD"
    http = 422

    def __init__(self, minimum: int) -> None:
        """Build the error, stating the rule rather than merely refusing."""
        super().__init__(f"A senha precisa ter ao menos {minimum} caracteres.")


class EmailAlreadyRegistered(DomainError):
    """An account already exists for this address, in any status (AC-0001-28)."""

    code = "EMAIL_ALREADY_REGISTERED"
    http = 409

    def __init__(self) -> None:
        """Build the error, naming the reset path rather than a second invite."""
        super().__init__(
            "Já existe uma conta para este e-mail. Se a pessoa esqueceu a senha, "
            "use 'redefinir senha' em vez de convidar de novo."
        )


class NonInstitutionalDomain(DomainError):
    """The invited address is outside the institutional domains (AC-0001-28)."""

    code = "NON_INSTITUTIONAL_DOMAIN"
    http = 422

    def __init__(self, allowed: list[str]) -> None:
        """Build the error, listing the domains so the gestor can correct it."""
        super().__init__(f"Use um e-mail institucional. Domínios aceitos: {', '.join(allowed)}.")


class UsuarioNotFound(DomainError):
    """No usuario matches the identifier supplied.

    Shares `NOT_FOUND` with `RouteUnavailable` on purpose. Both mean "there is
    nothing here" and both carry the same message, so two codes would give a
    client switching on `code` two values for one outcome while telling it
    nothing extra. The distinction that matters to a caller is the status, and
    that is identical too.
    """

    code = "NOT_FOUND"
    http = 404

    def __init__(self) -> None:
        """Build the error. It says nothing about whether the id ever existed."""
        super().__init__("Recurso não encontrado.")


class LastGestor(DomainError):
    """The change would leave no active gestor (AC-0001-29, RN16).

    Blocking or demoting the only active gestor locks the entity out of its own
    member management, with no path back that does not involve database access.
    """

    code = "ULTIMO_GESTOR"
    http = 409

    def __init__(self) -> None:
        """Build the error, naming the remedy rather than only refusing."""
        super().__init__(
            "Esta é a única conta de gestor ativa. Promova outro gestor antes de "
            "bloquear ou desativar esta."
        )


class ResetAlreadyUsed(DomainError):
    """The reset grant was already redeemed, or never existed (AC-0001-31)."""

    code = "RESET_ALREADY_USED"
    http = 409

    def __init__(self) -> None:
        """Build the error, which does not distinguish spent from unknown."""
        super().__init__("Este link de redefinição já foi usado. Solicite outro.")


class ResetExpired(DomainError):
    """The reset grant timed out, or a newer one superseded it (AC-0001-31)."""

    code = "RESET_EXPIRED"
    http = 409

    def __init__(self) -> None:
        """Build the error, pointing at requesting another."""
        super().__init__("Este link de redefinição expirou. Solicite outro.")


class RateLimited(DomainError):
    """The source exceeded this route's ceiling for the window (AC-0001-33).

    The message carries no count and names no throttle. Telling the caller how
    close they were, or which of the two limits fired, is a measuring instrument
    handed to whoever is probing (ADR-0012 §5). `Retry-After` is the only
    signal, and it reaches the client through the envelope handler.
    """

    code = "RATE_LIMITED"
    http = 429

    def __init__(self, *, retry_after: int) -> None:
        """Build the error, carrying only when to try again."""
        super().__init__(
            "Muitas requisições. Tente novamente em instantes.", retry_after=retry_after
        )
