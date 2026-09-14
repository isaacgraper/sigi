"""Who is calling, and whether they still may.

AC-0001-08 is the whole point of this module: `usuario.ativo` is checked on
**every** request, not only at login. That costs one indexed lookup per
authenticated call, and it is the difference between a deactivation that takes
effect now and one that takes effect in up to fifteen minutes — which is not a
deactivation.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Sequence
from typing import Annotated

from fastapi import Depends, Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.applications import Starlette

from app.core.correlacao import atual
from app.core.db import get_sessao
from app.core.seguranca import TokenInvalido, verify_access_token
from app.models.usuario import PERFIS, Usuario
from app.repositories import usuario as repo
from app.services.erros import PerfilNaoAutorizado, UsuarioInativo

ESQUEMA = "bearer"


def _token_do_cabecalho(request: Request) -> str:
    header = request.headers.get("authorization", "")
    tipo, _, valor = header.partition(" ")
    if tipo.lower() != ESQUEMA or not valor.strip():
        raise TokenInvalido("Sua sessão não é válida. Entre novamente.")
    return valor.strip()


def current_usuario(request: Request, sessao: Annotated[Session, Depends(get_sessao)]) -> Usuario:
    claims = verify_access_token(_token_do_cabecalho(request))
    usuario = repo.by_id(sessao, claims.usuario_id)
    if usuario is None or not usuario.ativo:
        # Same response whether the account was deleted, blocked or deactivated:
        # the caller holds a valid signature, so they already know the account
        # existed, but they learn nothing further about its state.
        raise UsuarioInativo()
    return usuario


UsuarioAtual = Annotated[Usuario, Depends(current_usuario)]


# ── The permission matrix (AC-0001-15 to -18, -23) ──────────────────────────
#
# The decision lives on the route, not in a parallel table. A separate table is
# the thing that ages: someone adds an endpoint, forgets the row, and the
# endpoint ends up with no decision at all. Here a route cannot start without
# declaring one, and AC-0001-23 is that check, run when the app is assembled.


class Decisao:
    """Base for access declarations. Its presence is the contract."""

    def descricao(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError


class Publica(Decisao):
    """A route deliberately left unauthenticated.

    Explicit on purpose: without it, "has no decision" and "was decided to be
    open" would be the same state, and forgetting would default to open access.
    A missing entry defaults to refusal, never to permission.
    """

    def __call__(self) -> None:
        return None

    def descricao(self) -> str:
        return "public"


class Exige(Decisao):
    """Requires authentication, and optionally a set of perfis."""

    def __init__(self, *perfis: str) -> None:
        desconhecidos = set(perfis) - set(PERFIS)
        if desconhecidos:
            # A mistyped perfil would refuse everybody, for ever, silently.
            # Better not to start.
            raise ValueError(f"perfis not in the matrix: {sorted(desconhecidos)}")
        self.perfis = frozenset(perfis)

    def __call__(self, request: Request, usuario: UsuarioAtual) -> Usuario:
        if self.perfis and usuario.perfil not in self.perfis:
            _auditar_recusa(request, usuario)
            raise PerfilNaoAutorizado()
        return usuario

    def descricao(self) -> str:
        return ", ".join(sorted(self.perfis)) if self.perfis else "authenticated"


def _auditar_recusa(request: Request, usuario: Usuario) -> None:
    """AC-0001-18 — a 403 that leaves no trace is indistinguishable from an
    attack that never happened. In its own transaction, because the request is
    about to raise and take its own with it; nothing was mutated, so there is no
    mutation for the row to be attached to."""
    from app.services.auditoria import Evento, record_standalone

    rota = request.scope.get("route")
    record_standalone(
        Evento(
            entidade_tipo="usuario",
            entidade_id=usuario.id,
            acao="auth.negada",
            usuario_id=usuario.id,
            dados_anteriores={
                # The declared path, not the concrete one: an id in the route
                # is business data, and the audit table can never be corrected.
                "rota": getattr(rota, "path", request.url.path),
                "metodo": request.method,
                "perfil": usuario.perfil,
            },
        ),
        correlation_id=_correlation_id(request),
    )


def _correlation_id(request: Request) -> uuid.UUID:
    bruto = request.scope.get("state", {}).get("correlation_id")
    return bruto if isinstance(bruto, uuid.UUID) else atual()


METODOS_DE_ESCRITA = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def route_decisions(rota: APIRoute) -> list[Decisao]:
    """Toda `Decisao` alcançável a partir da rota, inclusive aninhada."""

    def descend(dependente: Dependant) -> list[Decisao]:
        encontradas: list[Decisao] = (
            [dependente.call] if isinstance(dependente.call, Decisao) else []
        )
        return encontradas + [d for sub in dependente.dependencies for d in descend(sub)]

    return descend(rota.dependant)


class RotaSemDecisao(RuntimeError):
    """Uma rota de escrita subiu sem declarar quem pode chamá-la."""


def app_routes(app: Starlette) -> Iterator[tuple[str, APIRoute]]:
    """Every `APIRoute` in the app, with the full path already resolved.

    Descending is mandatory: since FastAPI 0.141 `include_router` no longer
    flattens routes into `app.routes` — it leaves a wrapper holding the original
    router. A shallow sweep would find no write route at all, and AC-0001-23
    would pass vacuously, reporting "everything is covered" about an empty list.
    The access is duck-typed on purpose: this internal shape has already changed
    once.
    """

    def descend(rotas: Sequence[object], prefixo: str = "") -> Iterator[tuple[str, APIRoute]]:
        for rota in rotas:
            if isinstance(rota, APIRoute):
                yield prefixo + rota.path, rota
                continue
            interno = getattr(rota, "original_router", None)
            if interno is not None:
                contexto = getattr(rota, "include_context", None)
                yield from descend(interno.routes, prefixo + getattr(contexto, "prefix", ""))
            elif hasattr(rota, "routes"):
                yield from descend(rota.routes, prefixo + str(getattr(rota, "path", "")))

    yield from descend(app.routes)


def verify_coverage(app: Starlette) -> None:
    """AC-0001-23 — no write route starts without an access decision.

    Runs at application assembly, so it breaks the build rather than
    production. It is what keeps AC-0001-15/-16/-17 honest as the system grows:
    an endpoint added without a decision is a hole nobody chose to open.
    """
    missing = [
        f"{metodo} {path}"
        for path, rota in app_routes(app)
        for metodo in sorted((rota.methods or set()) & METODOS_DE_ESCRITA)
        if not route_decisions(rota)
    ]
    if missing:
        raise RotaSemDecisao(
            "write routes with no access decision: "
            + ", ".join(missing)
            + ". Declare one: Depends(Exige('gestor')), or Depends(Publica()) "
            "when the route is deliberately open."
        )
