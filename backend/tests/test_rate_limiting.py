"""Per-source rate limiting — AC-0001-33.

The second of two independent throttles. Several of these tests exist to prove
that independence, because a single throttle dressed up as two is the easiest
way to satisfy the criterion's words while missing its point.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from collections.abc import Callable, Iterator

import psycopg
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.throttling import RouteWithoutCeiling, enforce, verify_ceilings
from app.models.user import User
from app.services import throttle
from app.services.errors import RateLimited

LOGIN = "/api/v1/auth/login"
SENHA = "SenhaLongaOSuficiente-2026"


@pytest.fixture
def teto_baixo(monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    """Drop the login ceiling to something a test can reach in a few requests."""
    from app.core.config import get_settings

    cfg = get_settings()
    monkeypatch.setitem(cfg.rate_limit_tetos, LOGIN, 3)
    yield 3


def test_ac_0001_33_the_ceiling_refuses_with_retry_after(
    application: TestClient, teto_baixo: int
) -> None:
    """AC-0001-33 — 429 past the ceiling, and `Retry-After` is the only signal."""
    body = {"email": "ninguem@sc.gov.br", "password": "qualquer-coisa-longa"}

    for _ in range(teto_baixo):
        assert application.post(LOGIN, json=body).status_code == 401

    barrado = application.post(LOGIN, json=body)
    assert barrado.status_code == 429
    assert barrado.json()["error"]["code"] == "RATE_LIMITED"
    assert int(barrado.headers["Retry-After"]) >= 1


def test_ac_0001_33_the_body_says_nothing_measurable(
    application: TestClient, teto_baixo: int
) -> None:
    """The 429 names no throttle and carries no count.

    Either would be a measuring instrument handed to whoever is probing
    (ADR-0012 §5).
    """
    body = {"email": "ninguem@sc.gov.br", "password": "qualquer-coisa-longa"}
    for _ in range(teto_baixo + 1):
        response = application.post(LOGIN, json=body)

    assert response.status_code == 429
    erro = response.json()["error"]
    # The message only: the correlation id is a UUID and would match almost any
    # digit by chance, which would make this assertion pass for the wrong reason.
    mensagem = erro["message"].lower()
    assert str(teto_baixo) not in mensagem
    assert "limite_taxa" not in mensagem
    assert "tentativa" not in mensagem
    assert "restante" not in mensagem
    # The envelope keys, and nothing else.
    assert set(erro) <= {"code", "message", "fields", "correlation_id"}


def test_ac_0001_33_the_event_is_audited_without_an_address(
    application: TestClient, teto_baixo: int, sessao: Session
) -> None:
    """AC-0001-33 — a distributed attempt is visible in the history.

    The source goes in as an HMAC: this table can never be corrected, and
    `lgpd.md` promises it carries no personal data.
    """
    body = {"email": "ninguem@sc.gov.br", "password": "qualquer-coisa-longa"}
    for _ in range(teto_baixo + 1):
        application.post(LOGIN, json=body)

    sessao.rollback()
    row = sessao.execute(
        text(
            "SELECT dados_anteriores::text FROM historico_movimentacao"
            " WHERE acao = 'auth.limite_excedido' ORDER BY ocorrido_em DESC LIMIT 1"
        )
    ).scalar_one()
    assert LOGIN in row
    assert "origem_hmac" in row
    assert "testclient" not in row


def test_ac_0001_33_an_institutional_source_gets_a_higher_ceiling() -> None:
    """AC-0001-33 — a higher ceiling, never an exemption (ADR-0012 §4).

    Asserted on the selection function rather than over HTTP, because
    `TestClient` cannot present an arbitrary source address.
    """
    ordinary = throttle.ceiling_for(LOGIN, institutional=False)
    institutional = throttle.ceiling_for(LOGIN, institutional=True)

    assert institutional > ordinary
    # Not an exemption: an attacker who reaches the internal network still
    # meets a limit, which is when limits matter most.
    assert institutional < 10**9


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("10.1.2.3", True),
        ("192.168.4.5", True),
        ("172.16.0.1", True),
        ("8.8.8.8", False),
        ("127.0.0.1", False),
        ("testclient", False),
        ("", False),
        ("nao-e-um-ip", False),
    ],
)
def test_an_unreadable_source_is_treated_as_ordinary(source: str, expected: bool) -> None:
    """The direction of the guess matters.

    Defaulting to "institutional" would hand the higher ceiling to anyone who
    can make their source unreadable.
    """
    assert throttle.is_institutional(source) is expected


def test_the_window_is_fixed_and_floored() -> None:
    """A burst straddling a boundary sees two windows, which is the known cost."""
    seconds = 60
    a = throttle.window_start(
        datetime.datetime(2026, 9, 21, 12, 0, 59, tzinfo=datetime.UTC), seconds=seconds
    )
    b = throttle.window_start(
        datetime.datetime(2026, 9, 21, 12, 1, 0, tzinfo=datetime.UTC), seconds=seconds
    )
    assert a == datetime.datetime(2026, 9, 21, 12, 0, 0, tzinfo=datetime.UTC)
    assert b == datetime.datetime(2026, 9, 21, 12, 1, 0, tzinfo=datetime.UTC)
    assert a != b


def test_ac_0001_33_a_route_without_a_ceiling_breaks_the_build() -> None:
    """AC-0001-33's last clause, and the negative control for it.

    Without this, a `verify_ceilings` that silently found nothing would leave
    every other test here green while covering no route at all. There is
    deliberately no default ceiling, which is what lets this fail.
    """
    app = FastAPI()

    @app.post("/api/v1/auth/new-route", dependencies=[Depends(enforce)])
    def _sem_teto() -> None:  # pragma: no cover - never called
        return None

    with pytest.raises(RouteWithoutCeiling) as erro:
        verify_ceilings(app)
    assert "/api/v1/auth/new-route" in str(erro.value)


def test_a_route_outside_the_throttled_prefixes_needs_no_ceiling() -> None:
    """`/usuarios` sits behind authentication and the permission matrix already."""
    app = FastAPI()

    @app.post("/api/v1/usuarios/algo")
    def _outra() -> None:  # pragma: no cover - never called
        return None

    verify_ceilings(app)


def test_the_real_application_has_a_ceiling_for_every_throttled_route(
    application: TestClient,
) -> None:
    """The check the build runs, asserted here so a failure names the route."""
    from app.core.authorization import application_routes
    from app.main import create_app

    app = create_app()
    throttled = [p for p, _ in application_routes(app) if p.startswith(throttle.PREFIXES)]
    # Guards against passing over an empty list.
    assert throttled, "no throttled route found: the route walk is broken"
    verify_ceilings(app)


# ── The two throttles are independent (ADR-0012 §2) ─────────────────────────


def test_the_lockout_still_fires_while_the_source_is_under_its_ceiling(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-03 is not subsumed by AC-0001-33.

    Six failures on one address, well under the source ceiling, still lock the
    address. A throttle-only implementation would miss the patient attack on a
    single account.
    """
    email = f"travado-{uuid.uuid4().hex[:8]}@sc.gov.br"
    criar_usuario(email=email, perfil="servidor", senha=SENHA)

    for _ in range(6):
        application.post(LOGIN, json={"email": email, "password": "errada-mas-longa"})
    travado = application.post(LOGIN, json={"email": email, "password": "errada-mas-longa"})

    assert travado.status_code == 429
    assert travado.json()["error"]["code"] == "ATTEMPTS_EXCEEDED"


def test_the_throttle_fires_on_a_spray_no_single_address_would_catch(
    application: TestClient, teto_baixo: int, sessao: Session
) -> None:
    """AC-0001-33 is not subsumed by AC-0001-03.

    One failure each against many different addresses: no address reaches five,
    so the lockout never fires, and only the per-source throttle sees it.
    """

    def locked() -> int:
        sessao.rollback()
        return int(
            sessao.execute(
                text("SELECT count(*) FROM tentativa_login WHERE bloqueado_ate IS NOT NULL")
            ).scalar_one()
        )

    # Measured as a delta, not as an absolute. Another test in this file locks
    # an address on purpose, and the suite shares one database, so asserting
    # "nothing is locked" would be asserting something about that test instead
    # of about this spray.
    antes = locked()

    for _ in range(teto_baixo + 1):
        response = application.post(
            LOGIN,
            json={
                "email": f"spray-{uuid.uuid4().hex[:8]}@sc.gov.br",
                "password": "errada-mas-longa",
            },
        )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert locked() == antes


def test_concurrent_requests_do_not_escape_the_ceiling(
    banco: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The single-statement increment is the whole point.

    Read-then-write would let parallel requests both read n and both write
    n + 1, and the ceiling would disappear for anyone who sends their requests
    at once rather than in series. Asserted at the service level, on separate
    connections, because that is where the statement lives.
    """
    from app.core.config import get_settings

    monkeypatch.setenv("DATABASE_URL", _sqlalchemy_url(banco[1]))
    get_settings.cache_clear()
    from app.core.db import reset_engine

    reset_engine()

    # A route of its own: filtering the row back out by `route_path` alone would
    # otherwise match whatever the HTTP tests above left under /auth/login.
    route_path = "/api/v1/auth/teste-concorrencia"
    cfg = get_settings()
    monkeypatch.setitem(cfg.rate_limit_tetos, route_path, 5)
    source = "203.0.113.7"
    now = datetime.datetime.now(datetime.UTC)

    Sessions = sessionmaker(bind=create_engine(_sqlalchemy_url(banco[1])))
    served: list[bool] = []
    guard = threading.Lock()

    def hit(saida: list[bool] = served, trava: threading.Lock = guard) -> None:
        try:
            with Sessions() as session:
                throttle.check(
                    session,
                    source=source,
                    route_path=route_path,
                    now=now,
                    correlation_id=uuid.uuid4(),
                )
            with trava:
                saida.append(True)
        except RateLimited:
            with trava:
                saida.append(False)

    threads = [threading.Thread(target=hit) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    reset_engine()
    get_settings.cache_clear()

    assert len(served) == 20
    # Exactly the ceiling gets through, never more, however they arrive.
    assert served.count(True) == 5, served

    with psycopg.connect(banco[0], autocommit=True) as c:
        total = c.execute(
            "SELECT contador FROM limite_taxa WHERE rota = %s", (route_path,)
        ).fetchone()
        assert total is not None and total[0] == 20


def _sqlalchemy_url(dsn: str) -> str:
    from tests.conftest import _para_sqlalchemy

    return _para_sqlalchemy(dsn)
