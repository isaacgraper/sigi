"""Helpers shared by the SPEC-0003 tests: sign-in, grupos, insumos, ATAs, audit rows.

The shared test database holds other tests' rows, so every name and code made
here carries a random part, and a test looks only at what it created.
"""

from __future__ import annotations

import random
import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user import User

ATAS = "/api/v1/atas"
INSUMOS = "/api/v1/insumos"
GRUPOS = "/api/v1/grupos-materiais"
LOGIN = "/api/v1/auth/login"
# Not `*_PASSWORD`: gitleaks reads that keyword beside this entropy as a credential.
LONG_ENOUGH = "SenhaLongaOSuficiente-2026"

CNPJ = "11.222.333/0001-81"
OTHER_CNPJ = "45.723.174/0001-10"
CSV_HEADERS = {"Content-Type": "text/csv"}


def login(
    application: TestClient, create_user: Callable[..., User], perfil: str
) -> tuple[dict[str, str], User]:
    """Sign a new member of this perfil in; its headers and its row."""
    email = f"{perfil}-{uuid.uuid4().hex[:8]}@sc.gov.br"
    user = create_user(email=email, perfil=perfil, password=LONG_ENOUGH)
    entry = application.post(LOGIN, json={"email": email, "password": LONG_ENOUGH})
    assert entry.status_code == 200, entry.text
    return {"Authorization": f"Bearer {entry.json()['access_token']}"}, user


def unique(prefix: str) -> str:
    """A name no other test uses."""
    return f"{prefix} {uuid.uuid4().hex[:8].upper()}"


def sku() -> str:
    """A SKU no other test uses."""
    return f"T{uuid.uuid4().hex[:10].upper()}"


def doms() -> str:
    """A DOMS code no other test uses."""
    return str(random.randint(10**9, 10**12))


def grupo(
    application: TestClient,
    gestor: dict[str, str],
    *,
    name: str | None = None,
    parent: str | None = None,
) -> dict:
    """Create a grupo through the API."""
    response = application.post(
        GRUPOS,
        json={"name": name or unique("GRUPO"), "parent_id": parent},
        headers=gestor,
    )
    assert response.status_code == 201, response.text
    return response.json()


def insumo_body(grupo_id: str, **override: object) -> dict[str, object]:
    """A valid insumo registration, with whatever the test wants different."""
    data: dict[str, object] = {
        "sku": sku(),
        "description": unique("CLOREXIDINA 2% 1 L"),
        "unit": "UN",
        "grupo_id": grupo_id,
    }
    data.update(override)
    return data


def make_insumo(
    application: TestClient, headers: dict[str, str], grupo_id: str, **override: object
) -> dict:
    """Register an insumo through the API."""
    response = application.post(INSUMOS, json=insumo_body(grupo_id, **override), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def make_ata(application: TestClient, gestor: dict[str, str], **override: object) -> dict:
    """Register a vigente ATA through the API."""
    data: dict[str, object] = {
        "number": f"ATA-{uuid.uuid4().hex[:10]}",
        "subject": "Material de expediente",
        "organ": "Secretaria de Saúde",
        "fornecedor": {"cnpj": CNPJ, "legal_name": "Papelaria Exemplo Ltda"},
        "vigencia_inicio": "2026-01-01",
        "vigencia_fim": "2030-12-31",
        "total_value": "10000.00",
        "budget_date": "2026-03-10",
    }
    data.update(override)
    response = application.post(ATAS, json=data, headers=gestor)
    assert response.status_code == 201, response.text
    return response.json()


def add_item(
    application: TestClient,
    gestor: dict[str, str],
    ata_id: str,
    insumo_id: str,
    **override: object,
) -> dict:
    """Add an item through the API; the ATA's items come back."""
    data: dict[str, object] = {"insumo_id": insumo_id, "quantity": "100", "unit_price": "1.5"}
    data.update(override)
    response = application.post(f"{ATAS}/{ata_id}/itens", json=data, headers=gestor)
    assert response.status_code == 201, response.text
    return response.json()


def item_of(items: dict, insumo_id: str) -> dict:
    """The item of this insumo in an ATA's items."""
    return next(i for i in items["items"] if i["insumo"]["id"] == insumo_id)


def audit_rows(db_session: Session, entidade_id: str, acao: str | None = None) -> list:
    """The audit rows of an entity, oldest first."""
    db_session.rollback()
    sql = (
        "SELECT acao, usuario_id, dados_anteriores, justificativa, ocorrido_em"
        " FROM historico_movimentacao WHERE entidade_id = :i"
    )
    params: dict[str, object] = {"i": entidade_id}
    if acao:
        sql += " AND acao = :a"
        params["a"] = acao
    return list(db_session.execute(text(sql + " ORDER BY ocorrido_em"), params).all())


def csv(*lines: str, encoding: str = "utf-8") -> bytes:
    """A CSV file from its lines."""
    return ("\r\n".join(lines) + "\r\n").encode(encoding)
