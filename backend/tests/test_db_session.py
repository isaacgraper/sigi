"""A write is committed before its answer leaves the server.

The client acts on the answer at once: the ATA page opens on the id a POST
returned and reads it (SPEC-0013 AC-0013-07). A commit that runs after the
response is sent leaves that read a moment in which the row does not exist yet.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import psycopg
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from app.models.user import User
from tests.catalogue import ATAS, login, new_cnpj


def test_ac_0013_07_a_write_is_committed_before_its_answer(
    application: TestClient,
    create_user: Callable[..., User],
    admin_connection: psycopg.Connection,
) -> None:
    """At the first byte of the 201, another connection already sees the new ATA."""
    gestor, _ = login(application, create_user, "gestor")
    number = f"ATA-{uuid.uuid4().hex[:10]}"
    seen: list[int] = []
    inner = application.app

    async def watched(scope: Scope, receive: Receive, send: Send) -> None:
        async def watch(message: Message) -> None:
            if message["type"] == "http.response.start" and scope.get("path") == ATAS:
                row = admin_connection.execute(
                    "SELECT count(*) FROM ata WHERE numero = %s", (number,)
                ).fetchone()
                seen.append(row[0] if row else 0)
            await send(message)

        await inner(scope, receive, watch)

    with TestClient(watched) as client:
        response = client.post(
            ATAS,
            json={
                "number": number,
                "subject": "Material de expediente",
                "organ": "Secretaria de Saúde",
                "fornecedor": {"cnpj": new_cnpj(), "legal_name": "Papelaria Exemplo Ltda"},
                "vigencia_inicio": "2026-01-01",
                "vigencia_fim": "2030-12-31",
                "total_value": "10000.00",
                "budget_date": "2026-03-10",
            },
            headers=gestor,
        )

    assert response.status_code == 201, response.text
    assert seen == [1]
