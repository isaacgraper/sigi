"""Migration 0008 — the ATA notices (SPEC-0008).

What the database itself holds when the service is bypassed: one notice per
ATA, reason and key, a known reason, and no way for the application to delete
a notice or rewrite who read it.
"""

from __future__ import annotations

from collections.abc import Callable

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.models.user import User
from tests.catalogue import login, make_ata


@pytest.fixture
def ata_id(application: TestClient, create_user: Callable[..., User]) -> str:
    """A fresh ATA, registered through the API."""
    gestor = login(application, create_user, "gestor")[0]
    return str(make_ata(application, gestor)["id"])


def insert(
    connection: psycopg.Connection, ata_id: str, motivo: str = "venceu", chave: str = "k"
) -> None:
    """A notice written straight to the table."""
    connection.execute(
        "INSERT INTO notificacao (ata_id, motivo, chave, criada_em) VALUES (%s, %s, %s, now())",
        (ata_id, motivo, chave),
    )


def test_AC_0008_02_one_notice_per_ata_reason_and_key(
    ata_id: str, admin_connection: psycopg.Connection
) -> None:
    """The second notice of the same reason and key is refused by the database."""
    insert(admin_connection, ata_id)

    with pytest.raises(psycopg.errors.UniqueViolation):
        insert(admin_connection, ata_id)


def test_AC_0008_01_an_unknown_reason_is_refused(
    ata_id: str, admin_connection: psycopg.Connection
) -> None:
    """Only the five reasons of AC-0008-01."""
    with pytest.raises(psycopg.errors.CheckViolation):
        insert(admin_connection, ata_id, motivo="qualquer")


@pytest.mark.parametrize("table", ["notificacao", "notificacao_leitura"])
def test_the_application_role_cannot_delete(table: str, app_connection: psycopg.Connection) -> None:
    """A notice and its reading are kept; the app role has no DELETE."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_connection.execute(f"DELETE FROM {table}")  # noqa: S608 - a fixed table name
