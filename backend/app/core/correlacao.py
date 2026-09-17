"""Correlation id, per request.

RNF12 wants one on every structured log line, and
`historico_movimentacao.correlation_id` is `NOT NULL` — so an audit row cannot
be written without one. Services receive it as an argument rather than reading
it from ambient state: a hidden dependency in the layer that owns the domain
rules is exactly the sort of thing that makes a test pass for the wrong reason.

The context variable exists for the logging middleware, which genuinely has no
other way to reach it.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.types import ASGIApp, Message, Receive, Scope, Send

CABECALHO = "X-Correlation-Id"

_atual: ContextVar[uuid.UUID | None] = ContextVar("correlation_id", default=None)


def atual() -> uuid.UUID:
    """The current request's correlation id, or a fresh one outside a request."""
    valor = _atual.get()
    return valor if valor is not None else uuid.uuid4()


class CorrelacaoMiddleware:
    """Accept an inbound correlation id, or mint one, and echo it back.

    Accepting the caller's value is what lets a request be followed across the
    frontend and the API; minting one when absent is what stops the audit row
    from being the first place anyone notices it was missing.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the ASGI app."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Put a correlation id on the request before anything else runs."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        entrada = _do_cabecalho(scope)
        correlation_id = entrada or uuid.uuid4()
        token = _atual.set(correlation_id)
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        async def enviar(mensagem: Message) -> None:
            if mensagem["type"] == "http.response.start":
                headers = list(mensagem.get("headers", []))
                headers.append((CABECALHO.lower().encode(), str(correlation_id).encode()))
                mensagem = {**mensagem, "headers": headers}
            await send(mensagem)

        try:
            await self.app(scope, receive, enviar)
        finally:
            _atual.reset(token)


def _do_cabecalho(scope: Scope) -> uuid.UUID | None:
    alvo = CABECALHO.lower().encode()
    for nome, valor in scope.get("headers", []):
        if nome.lower() == alvo:
            try:
                return uuid.UUID(valor.decode())
            except ValueError:
                # A malformed inbound value is discarded rather than rejected:
                # it is a tracing convenience, not an authorisation input.
                return None
    return None
