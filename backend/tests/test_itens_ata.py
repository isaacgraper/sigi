"""The items of an ATA and the aditivo de quantidade — SPEC-0003 v1.1 §3.5, §3.6.

AC-0003-25, an item locked by an NE, is deferred to SPEC-0004 and has no test here.
"""

from __future__ import annotations

import decimal
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user import User
from tests.catalogue import (
    ATAS,
    add_item,
    audit_rows,
    grupo,
    item_of,
    login,
    make_ata,
    make_insumo,
    new_cnpj,
)


@pytest.fixture
def gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in gestor."""
    return login(application, create_user, "gestor")[0]


@pytest.fixture
def raiz(application: TestClient, gestor: dict[str, str]) -> dict:
    """A nivel 1 grupo of this test's own."""
    return grupo(application, gestor)


@pytest.fixture
def ata(application: TestClient, gestor: dict[str, str]) -> dict:
    """A vigente ATA of this test's own."""
    return make_ata(application, gestor)


def _post_item(
    application: TestClient, gestor: dict[str, str], ata_id: str, **data: object
) -> object:
    return application.post(f"{ATAS}/{ata_id}/itens", json=data, headers=gestor)


def _aditivo(
    application: TestClient, gestor: dict[str, str], ata_id: str, item_id: str, quantity: str
) -> object:
    return application.post(
        f"{ATAS}/{ata_id}/aditivos",
        json={
            "kind": "quantidade",
            "item_id": item_id,
            "quantity": quantity,
            "justification": "Acréscimo de quantitativo.",
        },
        headers=gestor,
    )


# ── AC-0003-20, -21 — adding an item and its value ──────────────────────────


def test_ac_0003_20_a_gestor_adds_an_item_at_five_decimals(
    application: TestClient,
    gestor: dict[str, str],
    raiz: dict,
    ata: dict,
    db_session: Session,
) -> None:
    """AC-0003-20 — 0,00599 stored exactly, 1.000 of it worth R$ 5,99, and audited."""
    insumo = make_insumo(application, gestor, raiz["id"])

    items = add_item(
        application,
        gestor,
        ata["id"],
        insumo["id"],
        quantity="1000",
        unit_price="0.00599",
        item_number="12",
    )

    item = item_of(items, insumo["id"])
    assert decimal.Decimal(item["unit_price"]) == decimal.Decimal("0.00599")
    assert decimal.Decimal(item["total_value"]) == decimal.Decimal("5.99")
    assert item["item_number"] == "12"
    stored = db_session.execute(
        text("SELECT valor_unitario::text FROM item_ata WHERE id = :i"), {"i": item["id"]}
    ).scalar_one()
    assert stored == "0.00599"
    rows = audit_rows(db_session, ata["id"], "ata.item_adicionado")
    assert rows[0].dados_anteriores == {"item_ata_id": item["id"], "sku": insumo["sku"]}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quantity", "0"),
        ("quantity", "-1"),
        ("quantity", "1.0001"),
        ("unit_price", "0"),
        ("unit_price", "-0.5"),
        ("unit_price", "0.000001"),
    ],
)
def test_ac_0003_20_a_bad_quantity_or_price_is_refused_not_rounded(
    application: TestClient,
    gestor: dict[str, str],
    raiz: dict,
    ata: dict,
    field: str,
    value: str,
) -> None:
    """AC-0003-20 — 422 naming the field: positive, three places for quantity, five for price."""
    insumo = make_insumo(application, gestor, raiz["id"])
    data = {"insumo_id": insumo["id"], "quantity": "10", "unit_price": "1.5", field: value}

    response = _post_item(application, gestor, ata["id"], **data)

    assert response.status_code == 422  # type: ignore[attr-defined]
    assert field in response.json()["error"]["fields"]  # type: ignore[attr-defined]
    listed = application.get(f"{ATAS}/{ata['id']}/itens", headers=gestor).json()
    assert listed["items"] == []


def test_ac_0003_20_an_insumo_is_an_item_of_an_ata_once(
    application: TestClient, gestor: dict[str, str], raiz: dict, ata: dict
) -> None:
    """AC-0003-20 — 409 ITEM_ATA_DUPLICADO."""
    insumo = make_insumo(application, gestor, raiz["id"])
    add_item(application, gestor, ata["id"], insumo["id"])

    response = _post_item(
        application, gestor, ata["id"], insumo_id=insumo["id"], quantity="1", unit_price="1"
    )

    assert response.status_code == 409  # type: ignore[attr-defined]
    assert response.json()["error"]["code"] == "ITEM_ATA_DUPLICADO"  # type: ignore[attr-defined]


def test_ac_0003_20_items_follow_the_ata_edit_rule(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-20 — a suspensa ATA takes items; an encerrada or cancelada one is 409."""
    insumo = make_insumo(application, gestor, raiz["id"])
    suspensa = make_ata(application, gestor)
    application.post(f"{ATAS}/{suspensa['id']}/suspender", headers=gestor)
    add_item(application, gestor, suspensa["id"], insumo["id"])

    for move, body in (("encerrar", None), ("cancelar", {"justification": "Erro."})):
        closed = make_ata(application, gestor)
        application.post(f"{ATAS}/{closed['id']}/{move}", json=body, headers=gestor)
        response = _post_item(
            application, gestor, closed["id"], insumo_id=insumo["id"], quantity="1", unit_price="1"
        )
        assert response.status_code == 409  # type: ignore[attr-defined]
        assert response.json()["error"]["code"] == "ATA_NAO_EDITAVEL"  # type: ignore[attr-defined]


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0003_20_only_a_gestor_adds_items(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    raiz: dict,
    ata: dict,
    perfil: str,
) -> None:
    """AC-0003-20 — 403 for a servidor and for an auditor."""
    insumo = make_insumo(application, gestor, raiz["id"])
    headers = login(application, create_user, perfil)[0]

    response = _post_item(
        application, headers, ata["id"], insumo_id=insumo["id"], quantity="1", unit_price="1"
    )

    assert response.status_code == 403  # type: ignore[attr-defined]


def test_ac_0003_21_the_value_is_rounded_once_half_up(
    application: TestClient, gestor: dict[str, str], raiz: dict, ata: dict, db_session: Session
) -> None:
    """AC-0003-21 — 3 × 0,33335 is R$ 1,00, and no column stores it."""
    insumo = make_insumo(application, gestor, raiz["id"])

    items = add_item(
        application, gestor, ata["id"], insumo["id"], quantity="3", unit_price="0.33335"
    )
    half = make_insumo(application, gestor, raiz["id"])
    items = add_item(application, gestor, ata["id"], half["id"], quantity="1", unit_price="0.005")

    assert decimal.Decimal(item_of(items, insumo["id"])["total_value"]) == decimal.Decimal("1.00")
    assert decimal.Decimal(item_of(items, half["id"])["total_value"]) == decimal.Decimal("0.01")
    columns = db_session.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'item_ata'")
    ).scalars()
    assert "valor_total" not in set(columns)


# ── AC-0003-22, -23 — the list, its sum, and the item's fornecedor ──────────


def test_ac_0003_22_items_are_listed_with_their_sum(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-22 — ordered by numero_item read as a number, then SKU; the sum differs."""
    ata = make_ata(application, gestor, total_value="10000.00")
    a = make_insumo(application, gestor, raiz["id"])
    b = make_insumo(application, gestor, raiz["id"])
    c = make_insumo(application, gestor, raiz["id"])
    add_item(
        application, gestor, ata["id"], a["id"], item_number="10", quantity="40", unit_price="200"
    )
    add_item(
        application, gestor, ata["id"], b["id"], item_number="2", quantity="16", unit_price="100"
    )
    items = add_item(application, gestor, ata["id"], c["id"], quantity="1", unit_price="200")

    assert [i["insumo"]["id"] for i in items["items"]] == [b["id"], a["id"], c["id"]]
    assert decimal.Decimal(items["items_value"]) == decimal.Decimal("9800.00")
    assert decimal.Decimal(items["total_value"]) == decimal.Decimal("10000.00")
    assert items["items_value_differs"] is True
    first = items["items"][0]
    assert {"sku", "description", "unit", "status"} <= set(first["insumo"])
    assert first["fornecedor"]["cnpj"] == "11222333000181"


def test_ac_0003_23_an_item_can_have_its_own_fornecedor(
    application: TestClient, gestor: dict[str, str], raiz: dict, ata: dict
) -> None:
    """AC-0003-23 — B on one item, A on the others; none, or A's own CNPJ, reads as A."""
    other = new_cnpj()
    a = make_insumo(application, gestor, raiz["id"])
    b = make_insumo(application, gestor, raiz["id"])
    c = make_insumo(application, gestor, raiz["id"])
    add_item(application, gestor, ata["id"], a["id"])
    add_item(
        application,
        gestor,
        ata["id"],
        b["id"],
        fornecedor={"cnpj": other, "legal_name": "Distribuidora B Ltda"},
    )
    items = add_item(
        application,
        gestor,
        ata["id"],
        c["id"],
        fornecedor={"cnpj": "11222333000181", "legal_name": "Papelaria Exemplo Ltda"},
    )

    assert item_of(items, a["id"])["fornecedor"]["cnpj"] == "11222333000181"
    assert item_of(items, a["id"])["own_fornecedor"] is False
    assert item_of(items, b["id"])["fornecedor"]["cnpj"] == other
    assert item_of(items, b["id"])["own_fornecedor"] is True
    assert item_of(items, c["id"])["own_fornecedor"] is False


# ── AC-0003-24 — correcting and removing ────────────────────────────────────


def test_ac_0003_24_a_gestor_corrects_an_item(
    application: TestClient, gestor: dict[str, str], raiz: dict, ata: dict, db_session: Session
) -> None:
    """AC-0003-24 — saved, with the prior values in the audit row."""
    insumo = make_insumo(application, gestor, raiz["id"])
    item = add_item(application, gestor, ata["id"], insumo["id"])["items"][0]

    response = application.patch(
        f"{ATAS}/{ata['id']}/itens/{item['id']}",
        json={"quantity": "120", "unit_price": "1.23456", "item_number": "7"},
        headers=gestor,
    )

    assert response.status_code == 200, response.text
    corrected = response.json()["items"][0]
    assert decimal.Decimal(corrected["quantity"]) == 120
    assert decimal.Decimal(corrected["unit_price"]) == decimal.Decimal("1.23456")
    rows = audit_rows(db_session, ata["id"], "ata.item_editado")
    assert rows[0].dados_anteriores == {
        "item_ata_id": item["id"],
        "quantidade": "100.000",
        "valor_unitario": "1.50000",
        "numero_item": None,
    }


def test_ac_0003_24_a_gestor_removes_an_item(
    application: TestClient, gestor: dict[str, str], raiz: dict, ata: dict, db_session: Session
) -> None:
    """AC-0003-24 — gone from the list and the sum, audited, and the insumo free again."""
    insumo = make_insumo(application, gestor, raiz["id"])
    item = add_item(application, gestor, ata["id"], insumo["id"])["items"][0]

    response = application.post(f"{ATAS}/{ata['id']}/itens/{item['id']}/remover", headers=gestor)

    assert response.status_code == 200, response.text
    assert response.json()["items"] == []
    assert decimal.Decimal(response.json()["items_value"]) == 0
    rows = audit_rows(db_session, ata["id"], "ata.item_removido")
    assert rows[0].dados_anteriores["sku"] == insumo["sku"]
    again = add_item(application, gestor, ata["id"], insumo["id"])
    assert len(again["items"]) == 1
    gone = application.post(f"{ATAS}/{ata['id']}/itens/{item['id']}/remover", headers=gestor)
    assert gone.status_code == 404


def test_ac_0003_24_items_of_a_closed_ata_are_not_corrected(
    application: TestClient, gestor: dict[str, str], raiz: dict, ata: dict
) -> None:
    """AC-0003-24 — 409 ATA_NAO_EDITAVEL once the ATA is encerrada."""
    insumo = make_insumo(application, gestor, raiz["id"])
    item = add_item(application, gestor, ata["id"], insumo["id"])["items"][0]
    application.post(f"{ATAS}/{ata['id']}/encerrar", headers=gestor)

    edit = application.patch(
        f"{ATAS}/{ata['id']}/itens/{item['id']}", json={"quantity": "1"}, headers=gestor
    )
    remove = application.post(f"{ATAS}/{ata['id']}/itens/{item['id']}/remover", headers=gestor)

    for response in (edit, remove):
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "ATA_NAO_EDITAVEL"


# ── AC-0003-27, -28 — aditivo de quantidade ─────────────────────────────────


def test_ac_0003_27_a_gestor_records_an_aditivo_de_quantidade(
    application: TestClient, gestor: dict[str, str], raiz: dict, ata: dict, db_session: Session
) -> None:
    """AC-0003-27 — contracted 120, quantidade still 100, the value aditivos untouched."""
    insumo = make_insumo(application, gestor, raiz["id"])
    item = add_item(application, gestor, ata["id"], insumo["id"], quantity="100")["items"][0]

    response = _aditivo(application, gestor, ata["id"], item["id"], "20")

    assert response.status_code == 201, response.text  # type: ignore[attr-defined]
    detail = response.json()  # type: ignore[attr-defined]
    assert detail["valor_contratado"] == ata["valor_contratado"]
    aditivo = detail["aditivos"][0]
    assert (aditivo["kind"], aditivo["item_id"]) == ("quantidade", item["id"])
    after = application.get(f"{ATAS}/{ata['id']}/itens", headers=gestor).json()["items"][0]
    assert decimal.Decimal(after["quantity"]) == 100
    assert decimal.Decimal(after["contracted_quantity"]) == 120
    rows = audit_rows(db_session, ata["id"], "ata.aditivo_registrado")
    assert rows[0].dados_anteriores["quantidade_contratada"] == "100.000"
    assert rows[0].justificativa == "Acréscimo de quantitativo."


def test_ac_0003_27_a_bad_aditivo_de_quantidade_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict, ata: dict
) -> None:
    """AC-0003-27 — no justification or no positive quantity is 422; not vigente is 409."""
    insumo = make_insumo(application, gestor, raiz["id"])
    item = add_item(application, gestor, ata["id"], insumo["id"])["items"][0]

    no_reason = application.post(
        f"{ATAS}/{ata['id']}/aditivos",
        json={"kind": "quantidade", "item_id": item["id"], "quantity": "1"},
        headers=gestor,
    )
    assert no_reason.status_code == 422
    for quantity in ("0", "-5"):
        response = _aditivo(application, gestor, ata["id"], item["id"], quantity)
        assert response.status_code == 422  # type: ignore[attr-defined]

    application.post(f"{ATAS}/{ata['id']}/suspender", headers=gestor)
    suspended = _aditivo(application, gestor, ata["id"], item["id"], "1")
    assert suspended.status_code == 409  # type: ignore[attr-defined]
    assert suspended.json()["error"]["code"] == "ATA_NAO_VIGENTE"  # type: ignore[attr-defined]


def test_ac_0003_28_rn15_the_ceiling_on_quantity_is_25_percent(
    application: TestClient, gestor: dict[str, str], raiz: dict, ata: dict
) -> None:
    """AC-0003-28, RN15 — 20 of 100 then 6 more is refused; nor may the quantity drop to 70."""
    insumo = make_insumo(application, gestor, raiz["id"])
    item = add_item(application, gestor, ata["id"], insumo["id"], quantity="100")["items"][0]
    assert _aditivo(application, gestor, ata["id"], item["id"], "20").status_code == 201  # type: ignore[attr-defined]

    over = _aditivo(application, gestor, ata["id"], item["id"], "6")
    shrink = application.patch(
        f"{ATAS}/{ata['id']}/itens/{item['id']}", json={"quantity": "70"}, headers=gestor
    )

    for response in (over, shrink):
        assert response.status_code == 422  # type: ignore[attr-defined]
        assert response.json()["error"]["code"] == "ADITIVO_ACIMA_DO_LIMITE"  # type: ignore[attr-defined]
    after = application.get(f"{ATAS}/{ata['id']}/itens", headers=gestor).json()["items"][0]
    assert decimal.Decimal(after["contracted_quantity"]) == 120
    assert _aditivo(application, gestor, ata["id"], item["id"], "5").status_code == 201  # type: ignore[attr-defined]
