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

    code: str = "ERRO_DOMINIO"
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


class CredenciaisInvalidas(DomainError):
    """Wrong password, unknown e-mail, or an address off the allowlist.

    One class for all three on purpose: AC-0001-02 requires the three responses
    to be byte-identical, and having separate classes is how they drift apart.
    """

    code = "CREDENCIAIS_INVALIDAS"
    http = 401

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("E-mail ou senha inválidos.")


class UsuarioInativo(DomainError):
    """The credential is right and the account is not ativo."""

    code = "USUARIO_INATIVO"
    http = 401

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("Esta conta não está ativa. Procure o gestor da sua unidade.")


class RefreshInvalido(DomainError):
    """The refresh token is unknown, expired, or already rotated."""

    code = "REFRESH_INVALIDO"
    http = 401

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("Sua sessão não é mais válida. Entre novamente.")


class RotaIndisponivel(DomainError):
    """A mechanism switched off by configuration (AC-0001-24).

    404 rather than 403: a mechanism that is off should be indistinguishable
    from one that was never built.
    """

    code = "NAO_ENCONTRADO"
    http = 404

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("Recurso não encontrado.")


class TentativasExcedidas(DomainError):
    """The address is locked after repeated failures (AC-0001-03).

    429 rather than 401: the caller is not being told their credential is
    wrong — this attempt was never evaluated.
    """

    code = "TENTATIVAS_EXCEDIDAS"
    http = 429

    def __init__(self, *, minutes: int) -> None:
        """Build the error, carrying the wait in seconds for `Retry-After`."""
        super().__init__(
            f"Muitas tentativas. Tente novamente em {minutes} minutos.",
            retry_after=minutes * 60,
        )
