"""The permission matrix, and the proof that every write route carries one.

AC-0001-15/-16/-17 walk the real route table, so they grow on their own as
routes are added. AC-0001-23 is the assembly-time check, and it needs a negative
control: a checker that checks nothing would leave the other tests green, which
is the exact failure the criterion exists to prevent.

AC-0001-16 and -17 are swept over the real route table at the bottom of this
file, per perfil, over HTTP. They used to share one unit test with AC-0001-15
that asserted far less than they state.

AC-0001-18 is asserted where it became observable, in
`test_users_invitations.py`: it needs a route that actually refuses, and when
this file was written every route was open.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import httpx2
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.authorization import (
    WRITE_METHODS,
    Public,
    Requires,
    RouteWithoutDecision,
    application_routes,
    route_decisions,
    verify_coverage,
)
from app.main import create_app
from app.models.user import User

SENHA_SWEEP = "SenhaLongaOSuficiente-2026"


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
def test_a_decision_admits_only_the_perfis_it_declares(perfil: str) -> None:
    """A unit check on the decision object, and nothing more.

    This used to be named for AC-0001-15/-16/-17 and claimed all three. It
    asserts a set on an object built here: no application, no route table, no
    HTTP status. The criteria are swept properly below; this keeps only the
    narrow guarantee it actually provides.
    """
    decision = Requires("gestor")
    assert (perfil in decision.perfis) == (perfil == "gestor")


def test_requires_with_no_perfil_means_merely_authenticated() -> None:
    """`Requires()` is a decision too: any signed-in caller, whatever the perfil."""
    assert Requires().describe() == "authenticated"
    assert Requires("gestor", "auditor").describe() == "auditor, gestor"
    assert Public().describe() == "public"


# ── AC-0001-15/-16/-17: the matrix, swept over the real route table ─────────
#
# Derived from `application_routes` rather than a hardcoded list, so a route
# added later is covered without anyone remembering to add it here. That is the
# difference between testing the matrix and testing a copy of it.


# SPEC-0001 §6, transcribed by hand. Reading the expectation off the route's own
# `Requires` would make this a tautology: the route would always agree with
# itself, and a route wired to the wrong perfil would pass. The whole point is
# to compare the application against the spec, so the spec has to be restated
# here and kept in step with §6 deliberately.
#
# None means "refuses nobody for reasons of perfil": `Public()` routes and
# `/auth/me`, which asks only for a valid session.
MATRIX: dict[tuple[str, str], frozenset[str] | None] = {
    ("POST", "/api/v1/auth/login"): None,
    ("POST", "/api/v1/auth/refresh"): None,
    ("POST", "/api/v1/auth/logout"): None,
    ("GET", "/api/v1/auth/me"): None,
    ("POST", "/api/v1/auth/redefinicoes/confirmar"): None,
    ("GET", "/api/v1/auth/oidc/authorize"): None,
    ("GET", "/api/v1/auth/oidc/callback"): None,
    ("POST", "/api/v1/convites/ativar"): None,
    ("GET", "/health"): None,
    # "Invite / activate / block / deactivate members" — gestor only.
    ("POST", "/api/v1/usuarios"): frozenset({"gestor"}),
    ("POST", "/api/v1/usuarios/{user_id}/bloquear"): frozenset({"gestor"}),
    ("POST", "/api/v1/usuarios/{user_id}/desativar"): frozenset({"gestor"}),
    # "Trigger a password reset for another member" — gestor only.
    ("POST", "/api/v1/usuarios/{user_id}/redefinir-senha"): frozenset({"gestor"}),
    # "View member list" — gestor, and auditor read-only.
    ("GET", "/api/v1/usuarios"): frozenset({"gestor", "auditor"}),
}


def test_the_matrix_covers_every_route_the_application_serves() -> None:
    """The transcription above must not fall behind the route table.

    A route absent from `MATRIX` would otherwise be skipped silently by the
    sweeps, which is the failure a hand-maintained expectation invites.
    """
    app = create_app()
    served = {
        (method, path)
        for path, route in application_routes(app)
        for method in (route.methods or set())
        if method != "HEAD"
    }
    assert served == set(MATRIX), (
        f"missing from MATRIX: {sorted(served - set(MATRIX))}; "
        f"stale in MATRIX: {sorted(set(MATRIX) - served)}"
    )


def _perfis_admitted(method: str, path: str) -> frozenset[str] | None:
    """What SPEC-0001 §6 says this route admits."""
    return MATRIX[(method, path)]


def _error_code(response: httpx2.Response) -> str | None:
    """The envelope's `code`, or None when the response carries no body.

    A 204 declares a JSON content type and sends nothing, so the header alone is
    not enough to decide whether there is anything to parse.
    """
    if not response.content:
        return None
    try:
        body = response.json()
    except ValueError:  # pragma: no cover - a non-JSON error page
        return None
    return body.get("error", {}).get("code") if isinstance(body, dict) else None


def _call(
    application: TestClient, method: str, path: str, headers: dict[str, str]
) -> httpx2.Response:
    # A real id in the placeholder, and an empty body. A route that gets past
    # authorisation then fails validation with 422, and 422 means "authorised".
    concrete = path.replace("{user_id}", str(uuid.uuid4()))
    if method == "GET":
        return application.get(concrete, headers=headers)
    return application.request(method, concrete, json={}, headers=headers)


def _headers_for(
    application: TestClient, criar_usuario: Callable[..., User], perfil: str
) -> dict[str, str]:
    email = f"{perfil}-sweep-{uuid.uuid4().hex[:8]}@sc.gov.br"
    criar_usuario(email=email, perfil=perfil, senha=SENHA_SWEEP)
    entrada = application.post("/api/v1/auth/login", json={"email": email, "password": SENHA_SWEEP})
    assert entrada.status_code == 200, entrada.text
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0001_16_17_every_write_route_holds_the_matrix(
    application: TestClient, criar_usuario: Callable[..., User], perfil: str
) -> None:
    """AC-0001-16/-17 — every write route, called as an `ativo` servidor and auditor.

    Each route the matrix denies must answer 403 `PERFIL_NAO_AUTORIZADO`, and no
    route it permits may be refused for reasons of perfil.

    This replaces a test that asserted `perfil in Requires("gestor").perfis` and
    claimed all three criteria. That checked a set on an object built in the
    test: it never called the application, never walked the route table and
    never saw an HTTP status, so it could not have caught a route wired without
    its decision. It asserted materially less than the criteria state.
    """
    headers = _headers_for(application, criar_usuario, perfil)
    app = create_app()

    swept = 0
    for path, route in application_routes(app):
        for method in sorted((route.methods or set()) & WRITE_METHODS):
            swept += 1
            admitted = _perfis_admitted(method, path)
            response = _call(application, method, path, headers)
            code = _error_code(response)

            if admitted is not None and perfil not in admitted:
                assert response.status_code == 403, f"{method} {path}: {response.text}"
                assert code == "PERFIL_NAO_AUTORIZADO", f"{method} {path}: {code}"
            else:
                # Anything but a refusal by perfil. 422 is the usual answer,
                # because the body is empty on purpose.
                assert not (response.status_code == 403 and code == "PERFIL_NAO_AUTORIZADO"), (
                    f"{method} {path} refused a permitted caller: {response.text}"
                )

    # Guards the loop against passing over an empty route table, which is how
    # AC-0001-23 would have passed vacuously before its own walk was fixed.
    assert swept >= 5, f"only {swept} write routes swept"


def test_ac_0001_17_an_auditor_keeps_the_read_routes_it_is_allowed(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-17's second clause — read-only means read, not nothing.

    Swept over every read route the matrix grants, not just one: §6 grants the
    auditor the member list explicitly ("auditor ✅ read-only"), and a test that
    only checked `/auth/me` would pass while that route refused them.
    """
    headers = _headers_for(application, criar_usuario, "auditor")
    app = create_app()

    checked = 0
    for path, route in application_routes(app):
        for method in sorted((route.methods or set()) - WRITE_METHODS - {"HEAD"}):
            admitted = _perfis_admitted(method, path)
            if admitted is not None and "auditor" not in admitted:
                continue
            checked += 1
            response = _call(application, method, path, headers)
            assert _error_code(response) != "PERFIL_NAO_AUTORIZADO", (
                f"{method} {path} refuses an auditor the matrix permits: {response.text}"
            )

    assert checked >= 2, f"only {checked} permitted read routes checked"


def test_ac_0001_15_a_gestor_is_refused_by_no_write_route(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-15 — the matrix holds for `gestor`: nothing refuses them by perfil."""
    headers = _headers_for(application, criar_usuario, "gestor")
    app = create_app()

    for path, route in application_routes(app):
        for method in sorted((route.methods or set()) & WRITE_METHODS):
            response = _call(application, method, path, headers)
            assert _error_code(response) != "PERFIL_NAO_AUTORIZADO", (
                f"{method} {path}: {response.text}"
            )
