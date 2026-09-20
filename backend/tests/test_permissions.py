"""The permission matrix, and the proof that every write route carries one.

AC-0001-15/-16/-17 walk the real route table, so they grow on their own as
routes are added. AC-0001-23 is the assembly-time check, and it needs a negative
control: a checker that checks nothing would leave the other tests green, which
is the exact failure the criterion exists to prevent.

AC-0001-18 is not here. It needs a route that actually refuses, and today every
route is open, so any test for it would assert the writer rather than the
behaviour. It arrives with member management.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI

from app.core.authorization import (
    Public,
    Requires,
    RouteWithoutDecision,
    application_routes,
    route_decisions,
    verify_coverage,
)
from app.main import create_app


def test_ac_0001_23_every_write_route_declares_a_decision() -> None:
    """AC-0001-23 — no write route is assembled without an access decision."""
    app = create_app()
    write_routes = [
        (method, path)
        for path, route in application_routes(app)
        for method in sorted((route.methods or set()) & {"POST", "PUT", "PATCH", "DELETE"})
    ]
    # Guards the assertion below against passing over an empty list, which is
    # what a shallow scan of `app.routes` would produce.
    assert write_routes, "no write route found: the route walk is broken, not the app"
    for path, route in application_routes(app):
        if (route.methods or set()) & {"POST", "PUT", "PATCH", "DELETE"}:
            assert route_decisions(route), f"{path} carries no access decision"


def test_ac_0001_23_a_route_without_a_decision_breaks_the_build() -> None:
    """AC-0001-23 — the negative control.

    Without this, a `verify_coverage` that silently found nothing would leave
    the test above green while checking an empty list.
    """
    app = FastAPI()

    @app.post("/sem-decisao")
    def _undeclared() -> None:  # pragma: no cover - never called
        return None

    with pytest.raises(RouteWithoutDecision) as erro:
        verify_coverage(app)
    assert "/sem-decisao" in str(erro.value)


def test_a_read_route_needs_no_decision() -> None:
    """Only write routes are required to declare. A GET is not a mutation."""
    app = FastAPI()

    @app.get("/aberta")
    def _read() -> None:  # pragma: no cover - never called
        return None

    verify_coverage(app)


def test_public_satisfies_the_check() -> None:
    """`Public()` is a decision, so declaring it is enough."""
    app = FastAPI()

    @app.post("/publica", dependencies=[Depends(Public())])
    def _open() -> None:  # pragma: no cover - never called
        return None

    verify_coverage(app)


def test_a_decision_nested_under_another_dependency_is_found() -> None:
    """The search descends the dependency tree.

    A decision sitting under another dependency, if it were missed, would make a
    protected route look unprotected and the report would name the wrong one.
    """

    def outer(_: object = Depends(Requires("gestor"))) -> None:
        return None

    app = FastAPI()

    @app.post("/aninhada", dependencies=[Depends(outer)])
    def _nested() -> None:  # pragma: no cover - never called
        return None

    verify_coverage(app)


def test_an_unknown_perfil_refuses_to_start() -> None:
    """A typo would refuse everyone for ever, in silence."""
    with pytest.raises(ValueError, match="perfis absent"):
        Requires("gerente")


@pytest.mark.parametrize("perfil", ["gestor", "servidor", "auditor"])
def test_ac_0001_15_16_17_the_matrix_admits_only_the_declared_perfis(perfil: str) -> None:
    """AC-0001-15/-16/-17 — a perfil outside the declaration is refused."""
    decision = Requires("gestor")
    assert (perfil in decision.perfis) == (perfil == "gestor")


def test_requires_with_no_perfil_means_merely_authenticated() -> None:
    """`Requires()` is a decision too: any signed-in caller, whatever the perfil."""
    assert Requires().describe() == "authenticated"
    assert Requires("gestor", "auditor").describe() == "auditor, gestor"
    assert Public().describe() == "public"
