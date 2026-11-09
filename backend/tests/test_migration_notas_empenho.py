"""Migration `0006_notas_empenho`: what the schema guarantees on its own.

DB2, DB4 and DB7 of `data-model.md`, and the rounding of a line, refused to the
owner itself, so a second writer cannot bypass the service (SPEC-0004 §11).
"""

from __future__ import annotations

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


def test_db2_an_item_of_another_ata_is_refused(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """DB2, AC-0004-21 — the trigger refuses a line whose item is of another ATA."""
    ata, items = setup_ata(application, gestor, [("10", "10")])
    _, other_items = setup_ata(application, gestor, [("10", "10")])
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")]).json()["id"]

    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute(
            "INSERT INTO item_nota_empenho (nota_empenho_id, item_ata_id, quantidade,"
            " valor_unitario, valor) VALUES (%s, %s, 1, 10, 10)",
            (ne_id, other_items[0]["id"]),
        )


def test_db4_an_ata_with_ne_in_progress_is_not_closed(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """DB4, AC-0004-25 — the trigger refuses closing past the service."""
    ata, items = setup_ata(application, gestor, [("10", "10")])
    open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")])

    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute("UPDATE ata SET status = 'encerrada' WHERE id = %s", (ata["id"],))


def test_db7_ne_without_items_does_not_leave_demanda(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """DB7, RN09 — an NE emptied in the database cannot be advanced."""
    ata, items = setup_ata(application, gestor, [("10", "10")])
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")]).json()["id"]
    admin_connection.execute("DELETE FROM item_nota_empenho WHERE nota_empenho_id = %s", (ne_id,))

    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute(
            "UPDATE nota_empenho SET status = 'validacao_saldo' WHERE id = %s", (ne_id,)
        )


def test_a_line_is_rounded_once_or_refused(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """ADR-0016 — a line whose valor is not round(quantidade × valor_unitario, 2) is refused."""
    ata, items = setup_ata(application, gestor, [("1000", "0.00599")])
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "3")]).json()["id"]

    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute(
            "UPDATE item_nota_empenho SET valor = 0.01 WHERE nota_empenho_id = %s", (ne_id,)
        )


def test_an_issued_ne_carries_both_numeros(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """AC-0004-28, -29 — the schema refuses an issued NE without its números."""
    ata, items = setup_ata(application, gestor, [("10", "10")])
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")]).json()["id"]
    to_stage(application, gestor, ne_id, "ne_emitida")

    for column in ("numero", "numero_pre_empenho", "data_emissao"):
        with pytest.raises(psycopg.errors.CheckViolation):
            admin_connection.execute(
                f"UPDATE nota_empenho SET {column} = NULL WHERE id = %s",  # noqa: S608
                (ne_id,),
            )


def test_the_application_role_cannot_delete_an_ne(
    application: TestClient, gestor: dict, app_connection: psycopg.Connection
) -> None:
    """An NE is cancelled, never deleted: the app role has no DELETE on the header."""
    ata, items = setup_ata(application, gestor, [("10", "10")])
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")]).json()["id"]

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_connection.execute("DELETE FROM nota_empenho WHERE id = %s", (ne_id,))
