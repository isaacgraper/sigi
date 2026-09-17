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
