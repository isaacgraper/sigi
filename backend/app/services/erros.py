"""Domain exceptions.

Services raise these; `app/api/erros.py` maps them to the envelope in
`api-conventions.md`. `CLAUDE.md` forbids raising `HTTPException` below the API
layer, which is what keeps the domain rules testable without a request.
"""

from __future__ import annotations


class ErroDominio(Exception):
    """Base for anything a caller did wrong.

    `codigo` is stable and machine-readable; `mensagem` is pt-BR, addressed to a
    servidor, and says what to do next. `campos` drives inline field errors — a
    single generic "dados inválidos" defeats the whole point, which is mitigating
    the transcription errors that motivated the project.
    """

    codigo: str = "ERRO_DOMINIO"
    http: int = 422

    def __init__(self, mensagem: str, *, campos: dict[str, str] | None = None) -> None:
        """Build the error with its pt-BR message and any per-field detail."""
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campos = campos or {}


class CredenciaisInvalidas(ErroDominio):
    """Wrong password, unknown e-mail, or an address off the allowlist.

    One class for all three on purpose: AC-0001-02 requires the three responses
    to be byte-identical, and having separate classes is how they drift apart.
    """

    codigo = "CREDENCIAIS_INVALIDAS"
    http = 401

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("E-mail ou senha inválidos.")


class UsuarioInativo(ErroDominio):
    """The credential is right and the account is not ativo."""

    codigo = "USUARIO_INATIVO"
    http = 401

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("Esta conta não está ativa. Procure o gestor da sua unidade.")


class RefreshInvalido(ErroDominio):
    """The refresh token is unknown, expired, or already rotated."""

    codigo = "REFRESH_INVALIDO"
    http = 401

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("Sua sessão não é mais válida. Entre novamente.")


class RotaIndisponivel(ErroDominio):
    """A mechanism switched off by configuration (AC-0001-24).

    404 rather than 403: a mechanism that is off should be indistinguishable
    from one that was never built.
    """

    codigo = "NAO_ENCONTRADO"
    http = 404

    def __init__(self) -> None:
        """Build the error with its message."""
        super().__init__("Recurso não encontrado.")
