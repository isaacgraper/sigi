"""Migration `0007_notas_fiscais`: what the schema guarantees on its own.

DB1, DB6 and DB14 of `data-model.md` and the CHECKs of both tables, refused to
the owner itself, so a second writer cannot bypass the service (SPEC-0005 §3).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.models.user import User
from tests.catalogue import login
from tests.test_notas_empenho import open_ne, setup_ata, to_stage


@pytest.fixture
def gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in gestor."""
    return login(application, create_user, "gestor")[0]


def issued_ne(application: TestClient, gestor: dict, stage: str = "ne_emitida") -> str:
    """An NE of one line of 10 × R$ 10,00 walked to `stage`; its id."""
    ata, items = setup_ata(application, gestor, [("100", "10")])
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "10")]).json()["id"]
    to_stage(application, gestor, ne_id, stage)
    return ne_id


def insert_nf(
    connection: psycopg.Connection,
    ne_id: str,
    *,
    numero: str | None = None,
    valor: str = "50.00",
    **columns: object,
) -> str:
    """INSERT an NF against `ne_id` as the owner, past the service; its id.

    The fornecedor is shared across tests, so the default número is fresh each call.
    """
    numero = numero or uuid.uuid4().hex[:12]
    names = ["numero", "data_emissao", "valor", "nota_empenho_id", *columns]
    values: list[object] = [numero, "2026-11-01", valor, ne_id, *columns.values()]
    row = connection.execute(
        f"INSERT INTO nota_fiscal ({', '.join(names)}, fornecedor_id, responsavel_id)"  # noqa: S608
        f" SELECT {', '.join(['%s'] * len(values))}, a.fornecedor_id, ne.responsavel_id"
        " FROM nota_empenho ne JOIN ata a ON a.id = ne.ata_id WHERE ne.id = %s RETURNING id",
        (*values, ne_id),
    ).fetchone()
    assert row is not None
    return str(row[0])


def test_db1_an_nf_of_an_ne_not_issued_is_refused(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """DB1, AC-0005-02 — the trigger refuses an NF bound to an NE before `ne_emitida`."""
    ne_id = issued_ne(application, gestor, "envio_fornecedor")

    with pytest.raises(psycopg.errors.CheckViolation):
        insert_nf(admin_connection, ne_id)


def test_db6_nfs_above_the_empenho_are_refused(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """DB6, RN12 — the NFs of an NE, `devolvida` excluded, never exceed its value."""
    ne_id = issued_ne(application, gestor)
    insert_nf(admin_connection, ne_id, valor="60.00")

    with pytest.raises(psycopg.errors.CheckViolation):
        insert_nf(admin_connection, ne_id, valor="40.01")


def test_db6_a_devolvida_nf_frees_its_value(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """DB6 — a `devolvida` NF does not count, and coming back from it is checked again."""
    ne_id = issued_ne(application, gestor)
    first = insert_nf(
        admin_connection,
        ne_id,
        valor="60.00",
        status="devolvida",
        justificativa_devolucao="Valor divergente.",
    )
    insert_nf(admin_connection, ne_id, valor="100.00")

    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute(
            "UPDATE nota_fiscal SET status = 'em_conferencia' WHERE id = %s", (first,)
        )


def test_db14_a_line_of_another_ne_is_refused(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """DB14 — an NF line naming a line of another NE is refused."""
    ne_id = issued_ne(application, gestor)
    other_ne = issued_ne(application, gestor)
    nf_id = insert_nf(admin_connection, ne_id)
    other_line = admin_connection.execute(
        "SELECT id FROM item_nota_empenho WHERE nota_empenho_id = %s", (other_ne,)
    ).fetchone()
    assert other_line is not None

    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute(
            "INSERT INTO item_nota_fiscal (nota_fiscal_id, item_nota_empenho_id, quantidade)"
            " VALUES (%s, %s, 1)",
            (nf_id, other_line[0]),
        )


@pytest.mark.parametrize(
    "columns",
    [
        {"status": "devolvida"},
        {"quarentena": True},
        {"motivo_quarentena": "Embalagem violada."},
        {"status": "paga"},
    ],
)
def test_the_nf_checks_hold(
    application: TestClient,
    gestor: dict,
    admin_connection: psycopg.Connection,
    columns: dict[str, object],
) -> None:
    """A devolução carries its justificativa and a quarentena exactly its motivo."""
    ne_id = issued_ne(application, gestor)

    with pytest.raises(psycopg.errors.CheckViolation):
        insert_nf(admin_connection, ne_id, **columns)


@pytest.mark.parametrize(("numero", "valor"), [("12-3", "10.00"), ("123", "0")])
def test_numero_and_valor_are_checked(
    application: TestClient,
    gestor: dict,
    admin_connection: psycopg.Connection,
    numero: str,
    valor: str,
) -> None:
    """The número is alphanumeric and the valor greater than zero."""
    ne_id = issued_ne(application, gestor)

    with pytest.raises(psycopg.errors.CheckViolation):
        insert_nf(admin_connection, ne_id, numero=numero, valor=valor)


def test_numero_is_unique_per_fornecedor(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """AC-0005-15 — the same número of the same fornecedor is refused."""
    ne_id = issued_ne(application, gestor)
    numero = uuid.uuid4().hex[:12]
    insert_nf(admin_connection, ne_id, numero=numero, valor="10.00")

    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_nf(admin_connection, ne_id, numero=numero, valor="10.00")


def test_the_application_role_cannot_delete_an_nf(
    application: TestClient,
    gestor: dict,
    admin_connection: psycopg.Connection,
    app_connection: psycopg.Connection,
) -> None:
    """An NF is returned, never deleted: the app role has no DELETE on the header."""
    nf_id = insert_nf(admin_connection, issued_ne(application, gestor))

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_connection.execute("DELETE FROM nota_fiscal WHERE id = %s", (nf_id,))
