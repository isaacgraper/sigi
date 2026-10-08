"""The first gestor, created from the command line (AC-0001-34, -35, -36).

Each test takes a database of its own: the criterion is about "no active gestor
exists", a property of the whole table, and the shared database holds many.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import psycopg
import pytest

from app import cli
from tests.conftest import APP_ROLE, _to_sqlalchemy

STRONG_ENOUGH = "SenhaLongaOSuficiente-2026"


@pytest.fixture
def operator_db(
    isolated_database: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> Iterator[psycopg.Connection]:
    """Point the application at an empty database and hand back an owner connection."""
    from app.core.config import get_settings
    from app.core.db import reset_engine

    monkeypatch.setenv("DATABASE_URL", _to_sqlalchemy(isolated_database[1]))
    monkeypatch.setenv("DB_APP_ROLE", APP_ROLE)
    get_settings.cache_clear()
    reset_engine()
    with psycopg.connect(isolated_database[0], autocommit=True) as admin:
        yield admin
    monkeypatch.undo()
    get_settings.cache_clear()
    reset_engine()


def _answers(*values: str) -> Callable[[str], str]:
    queue = list(values)
    return lambda _prompt: queue.pop(0)


def _gestores(admin: psycopg.Connection) -> list[tuple[str, str, bool]]:
    rows = admin.execute(
        "SELECT email, status, senha_hash IS NOT NULL FROM usuario WHERE perfil = 'gestor'"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def test_ac_0001_34_the_operator_creates_the_first_gestor(operator_db: psycopg.Connection) -> None:
    """AC-0001-34 — an active gestor exists, and the act is audited with no actor."""
    code = cli.bootstrap_gestor(
        "primeira@sc.gov.br",
        no_password=False,
        prompt=_answers(STRONG_ENOUGH, STRONG_ENOUGH),
    )

    assert code == 0
    assert _gestores(operator_db) == [("primeira@sc.gov.br", "ativo", True)]
    audit = operator_db.execute(
        "SELECT usuario_id, dados_anteriores FROM historico_movimentacao"
        " WHERE acao = 'usuario.gestor_inicial'"
    ).fetchall()
    assert audit == [(None, {"perfil": "gestor", "mecanismo": "local"})]


def test_ac_0001_34_an_oidc_only_install_needs_no_password(
    operator_db: psycopg.Connection,
) -> None:
    """With `--no-password` the gestor has no local credential."""
    assert cli.main(["bootstrap-gestor", "--email", "oidc@sc.gov.br", "--no-password"]) == 0
    assert _gestores(operator_db) == [("oidc@sc.gov.br", "ativo", False)]


def test_ac_0001_35_the_bootstrap_refuses_once_a_gestor_exists(
    operator_db: psycopg.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-0001-35 — a second run creates nobody."""
    cli.bootstrap_gestor("um@sc.gov.br", no_password=True)
    capsys.readouterr()

    code = cli.bootstrap_gestor("dois@sc.gov.br", no_password=True)

    assert code == 1
    assert "GESTOR_ALREADY_EXISTS" in capsys.readouterr().err
    assert [g[0] for g in _gestores(operator_db)] == ["um@sc.gov.br"]


@pytest.mark.parametrize(
    ("email", "password", "expected"),
    [
        ("alguem@gmail.com", None, "NON_INSTITUTIONAL_DOMAIN"),
        ("curta@sc.gov.br", "curta", "WEAK_PASSWORD"),
    ],
)
def test_ac_0001_36_the_bootstrap_holds_the_invitation_rules(
    operator_db: psycopg.Connection,
    capsys: pytest.CaptureFixture[str],
    email: str,
    password: str | None,
    expected: str,
) -> None:
    """AC-0001-36 — the same refusals an invitation gives, and nobody created."""
    code = cli.bootstrap_gestor(
        email,
        no_password=password is None,
        prompt=_answers(password or "", password or ""),
    )

    assert code == 1
    assert expected in capsys.readouterr().err
    assert _gestores(operator_db) == []


def test_ac_0001_36_an_address_already_registered_is_refused(
    operator_db: psycopg.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pending servidor's address cannot become the first gestor."""
    operator_db.execute(
        "INSERT INTO usuario (id, email, perfil, status)"
        " VALUES (gen_random_uuid(), %s, 'servidor', 'pendente')",
        ("ocupado@sc.gov.br",),
    )

    code = cli.bootstrap_gestor("ocupado@sc.gov.br", no_password=True)

    assert code == 1
    assert "EMAIL_ALREADY_REGISTERED" in capsys.readouterr().err
    assert _gestores(operator_db) == []


def test_differing_passwords_stop_before_the_database(operator_db: psycopg.Connection) -> None:
    """A typo in the confirmation creates nothing."""
    with pytest.raises(SystemExit, match="PASSWORDS_DIFFER"):
        cli.bootstrap_gestor(
            "gestor@sc.gov.br",
            no_password=False,
            prompt=_answers(STRONG_ENOUGH, STRONG_ENOUGH + "x"),
        )
    assert _gestores(operator_db) == []


# ── Development seed (AC-0001-39, -40) ─────────────────────────────────────


def test_ac_0001_39_a_development_install_has_a_known_gestor(
    operator_db: psycopg.Connection,
) -> None:
    """AC-0001-39 — admin@sc.gov.br exists, active, and a second run changes nothing."""
    assert cli.main(["seed-dev-admin"]) == 0
    assert cli.main(["seed-dev-admin"]) == 0

    assert _gestores(operator_db) == [("admin@sc.gov.br", "ativo", True)]
    from app.core.passwords import check_password

    stored = operator_db.execute(
        "SELECT senha_hash FROM usuario WHERE email = 'admin@sc.gov.br'"
    ).fetchone()
    assert stored is not None and check_password("admin", stored[0])


def test_ac_0001_40_the_seed_refuses_outside_development(
    operator_db: psycopg.Connection,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-0001-40 — any other APP_ENV creates nobody."""
    from app.core.config import get_settings

    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()

    assert cli.main(["seed-dev-admin"]) == 1
    assert "DEVELOPMENT_ONLY" in capsys.readouterr().err
    assert _gestores(operator_db) == []
