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

from app.core.correlation import current as current_correlation_id
from app.core.db import get_sessao
from app.core.security import TokenInvalido, verify_access_token
from app.models.user import PERFIS, User
from app.repositories import user as repo
from app.services.errors import InactiveUser, UnauthorizedPerfil

ESQUEMA = "bearer"


def _token_from_header(request: Request) -> str:
    cabecalho = request.headers.get("authorization", "")
    tipo, _, value = cabecalho.partition(" ")
    if tipo.lower() != ESQUEMA or not value.strip():
        raise TokenInvalido("Sua sessão não é válida. Entre novamente.")
    return value.strip()


def current_usuario(request: Request, session: Annotated[Session, Depends(get_sessao)]) -> User:
    """Resolve the bearer token to a user, and refuse one that is not ativo.

    The active check runs here, on every request, rather than only at login.
    Otherwise a deactivation would take up to fifteen minutes to bite, which is
    the life of the access token (AC-0001-08).
    """
    claims = verify_access_token(_token_from_header(request))
    user = repo.by_id(session, claims.usuario_id)
    if user is None or not user.ativo:
        # Same response whether the account was deleted, blocked or deactivated:
        # the caller holds a valid signature, so they already know the account
        # existed, but they learn nothing further about its state.
        raise InactiveUser()
    return user


UsuarioAtual = Annotated[User, Depends(current_usuario)]


# ── The permission matrix (AC-0001-15 to -18, -23) ──────────────────────────
#
# The decision lives on the route itself, never in a parallel table. A separate
# table is the thing that ages: somebody adds an endpoint, forgets the row, and
# the endpoint ends up with no decision at all. Here a route cannot start
# without declaring one, and AC-0001-23 is literally that check, run when the
# application is assembled.


class Decision:
    """Base of the access declarations. Its existence is the contract."""

    def describe(self) -> str:  # pragma: no cover - overridden
        """Name this decision, for the coverage report and the error message."""
        raise NotImplementedError


class Public(Decision):
    """A route deliberately served without authentication.

    It exists in order to be explicit. Without it, "has no decision" and
    "decided it is open" would be the same state, and forgetting would default
    to open access. A missing entry is a refusal, never a permission.
    """

    def __call__(self) -> None:
        """Satisfy the dependency without asserting anything about the caller."""
        return None

    def describe(self) -> str:
        """Name this decision for the coverage report."""
        return "public"


class Requires(Decision):
    """Requires authentication, and optionally a set of perfis."""

    def __init__(self, *perfis: str) -> None:
        """Declare who may call the route, refusing a perfil that does not exist."""
        unknown = set(perfis) - set(PERFIS)
        if unknown:
            # A typo in a perfil would refuse everyone for ever, in silence.
            # Better not to start at all.
            raise ValueError(f"perfis absent from the matrix: {sorted(unknown)}")
        self.perfis = frozenset(perfis)

    def __call__(self, request: Request, user: UsuarioAtual) -> User:
        """Refuse the call when the caller's perfil is not among the declared ones."""
        if self.perfis and user.role not in self.perfis:
            _audit_refusal(request, user)
            raise UnauthorizedPerfil()
        return user

    def describe(self) -> str:
        """Name the admitted perfis for the coverage report."""
        return ", ".join(sorted(self.perfis)) if self.perfis else "authenticated"


def _audit_refusal(request: Request, user: User) -> None:
    """Record a refusal by perfil (AC-0001-18).

    A 403 with no trace is indistinguishable from an attack that never
    happened. The row goes in a transaction of its own, because the request is
    about to raise and take its own transaction with it, and nothing was
    mutated for the row to ride along with.
    """
    from app.services.audit import Event, record_standalone

    route = request.scope.get("route")
    record_standalone(
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="auth.negada",
            usuario_id=user.id,
            dados_anteriores={
                # The declared path, not the concrete one: an id in the path is
                # business data, and the audit table cannot be corrected later.
                "rota": getattr(route, "path", request.url.path),
                "metodo": request.method,
                "perfil": user.role,
            },
        ),
        correlation_id=_correlation_id(request),
    )


def _correlation_id(request: Request) -> uuid.UUID:
    raw = request.scope.get("state", {}).get("correlation_id")
    return raw if isinstance(raw, uuid.UUID) else current_correlation_id()


WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def route_decisions(route: APIRoute) -> list[Decision]:
    """Every `Decision` reachable from the route, nested ones included."""

    def descend(dependant: Dependant) -> list[Decision]:
        found: list[Decision] = [dependant.call] if isinstance(dependant.call, Decision) else []
        return found + [d for sub in dependant.dependencies for d in descend(sub)]

    return descend(route.dependant)


class RouteWithoutDecision(RuntimeError):
    """A write route started without declaring who may call it."""


def application_routes(app: Starlette) -> Iterator[tuple[str, APIRoute]]:
    """Every `APIRoute` in the application, with its full path.

    Descending is not optional: since FastAPI 0.141 `include_router` no longer
    flattens routes into `app.routes`, it leaves a wrapper there with the
    original router inside. A shallow scan would see no write route at all, and
    AC-0001-23 would pass vacuously, reporting "all covered" about an empty
    list. The access is duck-typed on purpose, because the internal shape of
    this has already changed once.
    """

    def descend(routes: Sequence[object], prefix: str = "") -> Iterator[tuple[str, APIRoute]]:
        for route in routes:
            if isinstance(route, APIRoute):
                yield prefix + route.path, route
                continue
            inner = getattr(route, "original_router", None)
            if inner is not None:
                context = getattr(route, "include_context", None)
                yield from descend(inner.routes, prefix + getattr(context, "prefix", ""))
            elif hasattr(route, "routes"):
                yield from descend(route.routes, prefix + str(getattr(route, "path", "")))

    yield from descend(app.routes)


def verify_coverage(app: Starlette) -> None:
    """Refuse to start a write route with no access decision (AC-0001-23).

    Runs when the application is assembled, so it breaks the build and the test
    suite rather than production. It is what keeps AC-0001-15/-16/-17 honest as
    the system grows: an endpoint added without a decision is a hole nobody
    chose to open.
    """
    missing = [
        f"{method} {path}"
        for path, route in application_routes(app)
        for method in sorted((route.methods or set()) & WRITE_METHODS)
        if not route_decisions(route)
    ]
    if missing:
        raise RouteWithoutDecision(
            "write routes with no access decision: "
            + ", ".join(missing)
            + ". Declare one: Depends(Requires('gestor')), or Depends(Public()) "
            "when the route is deliberately open."
        )
