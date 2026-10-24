"""The catalogue, its grupos and RN07's scope — SPEC-0003 v1.1 §3.1 to §3.3, §3.7, §3.8.

The import is in `test_importacao.py` and the items of an ATA in `test_itens_ata.py`.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.catalogue import (
    ATAS,
    GRUPOS,
    INSUMOS,
    add_item,
    audit_rows,
    doms,
    grupo,
    insumo_body,
    login,
    make_ata,
    make_insumo,
    sku,
    unique,
)


@pytest.fixture
def gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in gestor."""
    return login(application, create_user, "gestor")[0]


@pytest.fixture
def auditor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in auditor."""
    return login(application, create_user, "auditor")[0]


@pytest.fixture
def raiz(application: TestClient, gestor: dict[str, str]) -> dict:
    """A nivel 1 grupo of this test's own."""
    return grupo(application, gestor)


def scoped_servidor(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    *grupo_ids: str,
) -> dict[str, str]:
    """A signed-in servidor that owns these grupos."""
    headers, user = login(application, create_user, "servidor")
    response = application.post(
        f"/api/v1/usuarios/{user.id}/grupos-materiais",
        json={"grupo_ids": list(grupo_ids)},
        headers=gestor,
    )
    assert response.status_code == 200, response.text
    return headers


# ── AC-0003-01 to -03 — registering ─────────────────────────────────────────


def test_ac_0003_01_a_gestor_registers_an_insumo(
    application: TestClient, gestor: dict[str, str], raiz: dict, db_session: Session
) -> None:
    """AC-0003-01 — 201 with the insumo, its optional fields, and an audit row."""
    code = doms()
    response = application.post(
        INSUMOS,
        json=insumo_body(
            raiz["id"], codigo_doms=code, external_code="3678", reference_quantity="500"
        ),
        headers=gestor,
    )

    assert response.status_code == 201, response.text
    insumo = response.json()
    assert insumo["codigo_doms"] == code
    assert insumo["external_code"] == "3678"
    assert decimal.Decimal(insumo["reference_quantity"]) == 500
    assert insumo["status"] == "ativo"
    assert [g["id"] for g in insumo["grupo_path"]] == [raiz["id"]]
    rows = audit_rows(db_session, insumo["id"], "insumo.criado")
    assert len(rows) == 1
    assert rows[0].dados_anteriores is None


def test_ac_0003_01_a_servidor_registers_an_insumo_in_its_grupos(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    raiz: dict,
) -> None:
    """AC-0003-01 — a servidor registers too, inside its grupos."""
    servidor = scoped_servidor(application, create_user, gestor, raiz["id"])

    response = application.post(INSUMOS, json=insumo_body(raiz["id"]), headers=servidor)

    assert response.status_code == 201, response.text


@pytest.mark.parametrize("missing", ["sku", "description", "unit", "grupo_id"])
def test_ac_0003_01_a_missing_field_is_named(
    application: TestClient, gestor: dict[str, str], raiz: dict, missing: str
) -> None:
    """AC-0003-01 — 422 INVALID_DATA with `fields` naming what is missing."""
    data = insumo_body(raiz["id"])
    del data[missing]

    response = application.post(INSUMOS, json=data, headers=gestor)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_DATA"
    assert missing in error["fields"]


def test_ac_0003_01_an_unknown_grupo_is_refused(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-01 — a grupo_id that names no grupo is a field error."""
    response = application.post(INSUMOS, json=insumo_body(str(uuid.uuid4())), headers=gestor)

    assert response.status_code == 422
    assert "grupo_id" in response.json()["error"]["fields"]


def test_ac_0003_01_an_auditor_cannot_register(
    application: TestClient, auditor: dict[str, str], gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-01 — 403 for an auditor."""
    response = application.post(INSUMOS, json=insumo_body(raiz["id"]), headers=auditor)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"


def test_ac_0003_02_the_sku_is_trimmed_and_uppercased(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-02 — " clordeg21 " is stored as "CLORDEG21"."""
    code = sku()

    insumo = make_insumo(application, gestor, raiz["id"], sku=f" {code.lower()} ")

    assert insumo["sku"] == code


@pytest.mark.parametrize("bad", ["CLOR-DEG", "CLOR DEG", "CLOR.21", "ÇÃO1"])
def test_ac_0003_02_a_malformed_sku_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict, bad: str
) -> None:
    """AC-0003-02 — INVALID_SKU, and the message shows an example."""
    response = application.post(INSUMOS, json=insumo_body(raiz["id"], sku=bad), headers=gestor)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_SKU"
    assert "CLORDEG21" in error["message"]


@pytest.mark.parametrize("bad", ["2888.0", "26 829", "A26829"])
def test_ac_0003_02_a_malformed_doms_code_is_refused_not_trimmed(
    application: TestClient, gestor: dict[str, str], raiz: dict, bad: str
) -> None:
    """AC-0003-02 — INVALID_DOMS_CODE; `2888.0` is not turned into `2888`."""
    response = application.post(
        INSUMOS, json=insumo_body(raiz["id"], codigo_doms=bad), headers=gestor
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DOMS_CODE"


def test_ac_0003_03_a_taken_sku_or_doms_code_names_the_existing_insumo(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-03 — 409 INSUMO_DUPLICADO naming the existing insumo; nothing created."""
    code = doms()
    first = make_insumo(application, gestor, raiz["id"], codigo_doms=code)

    by_sku = application.post(
        INSUMOS, json=insumo_body(raiz["id"], sku=first["sku"]), headers=gestor
    )
    by_doms = application.post(
        INSUMOS, json=insumo_body(raiz["id"], codigo_doms=code), headers=gestor
    )

    for response in (by_sku, by_doms):
        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "INSUMO_DUPLICADO"
        assert first["sku"] in error["message"]
    listed = application.get(INSUMOS, params={"q": code}, headers=gestor).json()
    assert listed["total"] == 1


def test_ac_0003_03_an_edit_to_a_taken_doms_code_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-03 — an edit is checked too."""
    code = doms()
    make_insumo(application, gestor, raiz["id"], codigo_doms=code)
    other = make_insumo(application, gestor, raiz["id"])

    response = application.patch(
        f"{INSUMOS}/{other['id']}", json={"codigo_doms": code}, headers=gestor
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUMO_DUPLICADO"


def test_ac_0003_03_a_scoped_servidor_is_told_only_that_the_code_is_taken(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    raiz: dict,
) -> None:
    """AC-0003-03 — outside its grupos the existing insumo is not named (AC-0003-29)."""
    hidden = make_insumo(application, gestor, raiz["id"])
    own = grupo(application, gestor)
    servidor = scoped_servidor(application, create_user, gestor, own["id"])

    response = application.post(
        INSUMOS, json=insumo_body(own["id"], sku=hidden["sku"]), headers=servidor
    )

    assert response.status_code == 409
    assert hidden["sku"] not in response.json()["error"]["message"]


# ── AC-0003-04 — changing a SKU ─────────────────────────────────────────────


def test_ac_0003_04_a_gestor_changes_a_sku_with_a_justification(
    application: TestClient, gestor: dict[str, str], raiz: dict, db_session: Session
) -> None:
    """AC-0003-04 — the SKU changes, every link holds, and the audit keeps the old one."""
    insumo = make_insumo(application, gestor, raiz["id"])
    ata = make_ata(application, gestor)
    add_item(application, gestor, ata["id"], insumo["id"])
    new = sku()

    response = application.post(
        f"{INSUMOS}/{insumo['id']}/alterar-sku",
        json={"sku": new, "justification": "Código da Branet definido após a compra."},
        headers=gestor,
    )

    assert response.status_code == 200, response.text
    assert response.json()["sku"] == new
    items = application.get(f"{ATAS}/{ata['id']}/itens", headers=gestor).json()
    assert items["items"][0]["insumo"]["sku"] == new
    rows = audit_rows(db_session, insumo["id"], "insumo.sku_alterado")
    assert len(rows) == 1
    assert rows[0].dados_anteriores == {"sku": insumo["sku"]}
    assert rows[0].justificativa == "Código da Branet definido após a compra."


def test_ac_0003_04_the_justification_is_required(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-04 — 422 INVALID_DATA naming the justification."""
    insumo = make_insumo(application, gestor, raiz["id"])

    response = application.post(
        f"{INSUMOS}/{insumo['id']}/alterar-sku", json={"sku": sku()}, headers=gestor
    )

    assert response.status_code == 422
    assert "justification" in response.json()["error"]["fields"]


def test_ac_0003_04_a_sku_of_another_insumo_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-04 — 409 as in AC-0003-03."""
    taken = make_insumo(application, gestor, raiz["id"])
    insumo = make_insumo(application, gestor, raiz["id"])

    response = application.post(
        f"{INSUMOS}/{insumo['id']}/alterar-sku",
        json={"sku": taken["sku"], "justification": "Correção."},
        headers=gestor,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUMO_DUPLICADO"


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0003_04_only_a_gestor_changes_a_sku(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    raiz: dict,
    perfil: str,
) -> None:
    """AC-0003-04 — 403 for a servidor and for an auditor."""
    insumo = make_insumo(application, gestor, raiz["id"])
    headers = login(application, create_user, perfil)[0]

    response = application.post(
        f"{INSUMOS}/{insumo['id']}/alterar-sku",
        json={"sku": sku(), "justification": "Correção."},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"


# ── AC-0003-05, -10, -11, -12 — the catalogue ───────────────────────────────


def test_ac_0003_05_quantidade_referencia_is_not_stock(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-05 — no item figure and no ATA figure moves with it."""
    insumo = make_insumo(application, gestor, raiz["id"], reference_quantity="500")
    ata = make_ata(application, gestor)
    before_items = add_item(application, gestor, ata["id"], insumo["id"])
    before_ata = application.get(f"{ATAS}/{ata['id']}", headers=gestor).json()

    for value in ("0", "999999", None):
        response = application.patch(
            f"{INSUMOS}/{insumo['id']}", json={"reference_quantity": value}, headers=gestor
        )
        assert response.status_code == 200, response.text

        after_items = application.get(f"{ATAS}/{ata['id']}/itens", headers=gestor).json()
        after_ata = application.get(f"{ATAS}/{ata['id']}", headers=gestor).json()
        assert after_items == before_items
        assert after_ata["valor_contratado"] == before_ata["valor_contratado"]


def test_ac_0003_10_no_insumo_is_deleted(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-10 — DELETE answers 405 and the insumo is still there."""
    insumo = make_insumo(application, gestor, raiz["id"])

    response = application.delete(f"{INSUMOS}/{insumo['id']}", headers=gestor)

    assert response.status_code == 405
    assert application.get(f"{INSUMOS}/{insumo['id']}", headers=gestor).status_code == 200


def test_ac_0003_11_a_servidor_corrects_an_insumo(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    raiz: dict,
    db_session: Session,
) -> None:
    """AC-0003-11 — the change is saved and the audit row holds the prior values."""
    other = grupo(application, gestor, parent=raiz["id"])
    servidor = scoped_servidor(application, create_user, gestor, raiz["id"])
    insumo = make_insumo(application, gestor, raiz["id"], unit="UN")

    response = application.patch(
        f"{INSUMOS}/{insumo['id']}",
        json={"unit": "CX", "description": "LUVA NITRÍLICA M", "grupo_id": other["id"]},
        headers=servidor,
    )

    assert response.status_code == 200, response.text
    assert response.json()["unit"] == "CX"
    rows = audit_rows(db_session, insumo["id"], "insumo.editado")
    assert len(rows) == 1
    assert rows[0].dados_anteriores == {
        "unidade": "UN",
        "descricao": insumo["description"],
        "grupo_id": raiz["id"],
    }


def test_ac_0003_11_an_edit_cannot_send_a_sku(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-11 — the SKU changes only by AC-0003-04."""
    insumo = make_insumo(application, gestor, raiz["id"])

    response = application.patch(f"{INSUMOS}/{insumo['id']}", json={"sku": sku()}, headers=gestor)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_DATA"
    assert "sku" in error["fields"]


def test_ac_0003_12_every_profile_searches_the_catalogue(
    application: TestClient,
    gestor: dict[str, str],
    auditor: dict[str, str],
    raiz: dict,
) -> None:
    """AC-0003-12 — by sku, DOMS code or descrição in any case; by grupo, below included."""
    sub = grupo(application, gestor, parent=raiz["id"])
    marker = uuid.uuid4().hex[:8].upper()
    code = doms()
    a = make_insumo(application, gestor, raiz["id"], description=f"CLOREXIDINA {marker}")
    b = make_insumo(application, gestor, sub["id"], codigo_doms=code)

    found = application.get(INSUMOS, params={"q": marker.lower()}, headers=auditor).json()
    assert [i["id"] for i in found["items"]] == [a["id"]]
    assert application.get(INSUMOS, params={"q": code}, headers=auditor).json()["total"] == 1

    in_grupo = application.get(INSUMOS, params={"grupo_id": raiz["id"]}, headers=gestor).json()
    assert {i["id"] for i in in_grupo["items"]} == {a["id"], b["id"]}
    assert [g["id"] for g in in_grupo["items"][0]["grupo_path"]][0] == raiz["id"]


def test_ac_0003_12_the_list_filters_by_situacao(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-12 — ativo, descontinuado and substituido are derived and filterable."""
    ativo = make_insumo(application, gestor, raiz["id"])
    gone = make_insumo(application, gestor, raiz["id"])
    replaced = make_insumo(application, gestor, raiz["id"])
    application.post(
        f"{INSUMOS}/{gone['id']}/descontinuar",
        json={"justification": "Fora de linha."},
        headers=gestor,
    )
    application.post(
        f"{INSUMOS}/{replaced['id']}/substituir",
        json={"substitute_id": ativo["id"], "justification": "Troca."},
        headers=gestor,
    )

    def ids(situacao: str) -> set[str]:
        page = application.get(
            INSUMOS, params={"grupo_id": raiz["id"], "status": situacao}, headers=gestor
        ).json()
        return {i["id"] for i in page["items"]}

    assert ids("ativo") == {ativo["id"]}
    assert ids("descontinuado") == {gone["id"]}
    assert ids("substituido") == {replaced["id"]}


def test_ac_0003_12_one_insumo_carries_its_atas(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-12 — the detail names the ATAs the insumo is an item of; 404 for none."""
    insumo = make_insumo(application, gestor, raiz["id"])
    ata = make_ata(application, gestor)
    add_item(application, gestor, ata["id"], insumo["id"], unit_price="0.00599")

    detail = application.get(f"{INSUMOS}/{insumo['id']}", headers=gestor).json()

    assert [(a["ata_id"], a["ata_number"]) for a in detail["atas"]] == [(ata["id"], ata["number"])]
    assert decimal.Decimal(detail["atas"][0]["unit_price"]) == decimal.Decimal("0.00599")
    missing = application.get(f"{INSUMOS}/{uuid.uuid4()}", headers=gestor)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"


# ── AC-0003-09, -13 — grupos ────────────────────────────────────────────────


def test_ac_0003_09_grupos_are_three_levels(
    application: TestClient, gestor: dict[str, str], auditor: dict[str, str], db_session: Session
) -> None:
    """AC-0003-09 — levels 1 to 3, a fourth refused, and the tree read by any profile."""
    top = grupo(application, gestor, name=unique("MATERIAL ODONTOLÓGICO"))
    middle = grupo(application, gestor, name=unique("RESTAURADORES"), parent=top["id"])
    bottom = grupo(application, gestor, parent=middle["id"])
    assert (top["level"], middle["level"], bottom["level"]) == (1, 2, 3)
    assert len(audit_rows(db_session, top["id"], "grupo_material.criado")) == 1

    fourth = application.post(
        GRUPOS, json={"name": unique("X"), "parent_id": bottom["id"]}, headers=gestor
    )
    assert fourth.status_code == 422
    assert "parent_id" in fourth.json()["error"]["fields"]

    tree = application.get(GRUPOS, headers=auditor).json()
    node = next(n for n in tree if n["id"] == top["id"])
    assert node["children"][0]["id"] == middle["id"]
    assert node["children"][0]["children"][0]["id"] == bottom["id"]


def test_ac_0003_09_a_sibling_name_is_unique_ignoring_case(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-09 — 409 DUPLICATE_GROUP for the same name, in any case, with spaces."""
    name = unique("Limpeza")
    grupo(application, gestor, name=name, parent=raiz["id"])

    response = application.post(
        GRUPOS, json={"name": f"  {name.upper()} ", "parent_id": raiz["id"]}, headers=gestor
    )
    root = grupo(application, gestor, name=unique("Raiz"))
    duplicate_root = application.post(GRUPOS, json={"name": root["name"]}, headers=gestor)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_GROUP"
    assert duplicate_root.status_code == 409


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0003_09_only_a_gestor_creates_a_grupo(
    application: TestClient, create_user: Callable[..., User], perfil: str
) -> None:
    """AC-0003-09 — 403 for a servidor and for an auditor."""
    headers = login(application, create_user, perfil)[0]

    response = application.post(GRUPOS, json={"name": unique("G")}, headers=headers)

    assert response.status_code == 403


def test_ac_0003_13_a_gestor_renames_a_grupo(
    application: TestClient, gestor: dict[str, str], raiz: dict, db_session: Session
) -> None:
    """AC-0003-13 — renamed, its insumos stay, audited; a sibling's name refused."""
    sibling = grupo(application, gestor, parent=raiz["id"])
    target = grupo(application, gestor, parent=raiz["id"])
    insumo = make_insumo(application, gestor, target["id"])
    new_name = unique("RENOMEADO")

    response = application.patch(
        f"{GRUPOS}/{target['id']}", json={"name": new_name}, headers=gestor
    )
    taken = application.patch(
        f"{GRUPOS}/{target['id']}", json={"name": sibling["name"]}, headers=gestor
    )

    assert response.status_code == 200, response.text
    detail = application.get(f"{INSUMOS}/{insumo['id']}", headers=gestor).json()
    assert detail["grupo_path"][-1]["name"] == new_name
    rows = audit_rows(db_session, target["id"], "grupo_material.editado")
    assert rows[0].dados_anteriores == {"nome": target["name"]}
    assert taken.status_code == 409
    assert taken.json()["error"]["code"] == "DUPLICATE_GROUP"


# ── AC-0003-14 to -17 — substitution and discontinuation ────────────────────


def test_ac_0003_14_a_gestor_discontinues_an_insumo(
    application: TestClient, gestor: dict[str, str], raiz: dict, db_session: Session
) -> None:
    """AC-0003-14 — descontinuado today, its items unchanged, audited."""
    insumo = make_insumo(application, gestor, raiz["id"])
    ata = make_ata(application, gestor)
    before = add_item(application, gestor, ata["id"], insumo["id"])

    response = application.post(
        f"{INSUMOS}/{insumo['id']}/descontinuar",
        json={"justification": "Fabricante parou de produzir."},
        headers=gestor,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "descontinuado"
    assert (
        body["discontinued_on"]
        == datetime.datetime.now(datetime.UTC)
        .astimezone(datetime.timezone(datetime.timedelta(hours=-3)))
        .date()
        .isoformat()
    )
    after = application.get(f"{ATAS}/{ata['id']}/itens", headers=gestor).json()
    assert after["items"][0]["id"] == before["items"][0]["id"]
    assert after["items"][0]["quantity"] == before["items"][0]["quantity"]
    rows = audit_rows(db_session, insumo["id"], "insumo.descontinuado")
    assert rows[0].justificativa == "Fabricante parou de produzir."


def test_ac_0003_14_the_justification_is_required(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-14 — 422 INVALID_DATA without one."""
    insumo = make_insumo(application, gestor, raiz["id"])

    response = application.post(f"{INSUMOS}/{insumo['id']}/descontinuar", json={}, headers=gestor)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DATA"


def test_ac_0003_15_a_gestor_records_a_substitution(
    application: TestClient, gestor: dict[str, str], raiz: dict, db_session: Session
) -> None:
    """AC-0003-15 — A points to B, keeps its own SKU and descrição, and is audited."""
    a = make_insumo(application, gestor, raiz["id"])
    b = make_insumo(application, gestor, raiz["id"])

    response = application.post(
        f"{INSUMOS}/{a['id']}/substituir",
        json={"substitute_id": b["id"], "justification": "Item substituído por item novo."},
        headers=gestor,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "substituido"
    assert body["substitute"]["id"] == b["id"]
    assert (body["sku"], body["description"]) == (a["sku"], a["description"])
    assert body["discontinued_on"] is not None
    rows = audit_rows(db_session, a["id"], "insumo.substituido")
    assert rows[0].dados_anteriores["substituto"] == b["sku"]


def test_ac_0003_15_the_substitute_must_be_another_ativo_insumo(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-15 — itself, or one not ativo, is 409 INVALID_SUBSTITUTE."""
    a = make_insumo(application, gestor, raiz["id"])
    gone = make_insumo(application, gestor, raiz["id"])
    application.post(
        f"{INSUMOS}/{gone['id']}/descontinuar", json={"justification": "Fora."}, headers=gestor
    )

    for target in (a["id"], gone["id"], str(uuid.uuid4())):
        response = application.post(
            f"{INSUMOS}/{a['id']}/substituir",
            json={"substitute_id": target, "justification": "Troca."},
            headers=gestor,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVALID_SUBSTITUTE"


def test_ac_0003_16_a_gestor_reactivates_an_insumo(
    application: TestClient, gestor: dict[str, str], raiz: dict, db_session: Session
) -> None:
    """AC-0003-16 — the date and the substitute are cleared, and the audit keeps them."""
    a = make_insumo(application, gestor, raiz["id"])
    b = make_insumo(application, gestor, raiz["id"])
    application.post(
        f"{INSUMOS}/{a['id']}/substituir",
        json={"substitute_id": b["id"], "justification": "Troca."},
        headers=gestor,
    )

    response = application.post(
        f"{INSUMOS}/{a['id']}/reativar",
        json={"justification": "Troca por engano."},
        headers=gestor,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["status"], body["substitute"], body["discontinued_on"]) == ("ativo", None, None)
    rows = audit_rows(db_session, a["id"], "insumo.reativado")
    assert rows[0].dados_anteriores["substituido_por_id"] == b["id"]
    assert rows[0].justificativa == "Troca por engano."


def test_ac_0003_17_a_discontinued_insumo_enters_no_new_item(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-17 — 409 naming the substitute; an item that already holds it stays."""
    old = make_insumo(application, gestor, raiz["id"])
    new = make_insumo(application, gestor, raiz["id"])
    held = make_ata(application, gestor)
    add_item(application, gestor, held["id"], old["id"])
    application.post(
        f"{INSUMOS}/{old['id']}/substituir",
        json={"substitute_id": new["id"], "justification": "Troca."},
        headers=gestor,
    )
    other = make_ata(application, gestor)

    response = application.post(
        f"{ATAS}/{other['id']}/itens",
        json={"insumo_id": old["id"], "quantity": "1", "unit_price": "1"},
        headers=gestor,
    )

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INSUMO_DESCONTINUADO"
    assert new["sku"] in error["message"]
    items = application.get(f"{ATAS}/{held['id']}/itens", headers=gestor).json()
    assert items["items"][0]["insumo"]["id"] == old["id"]
    assert items["items"][0]["insumo"]["status"] == "substituido"


# ── AC-0003-29, -30 — RN07, the grupo axis ──────────────────────────────────


def test_ac_0003_29_rn07_a_servidor_sees_the_insumos_of_its_grupos(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    auditor: dict[str, str],
) -> None:
    """AC-0003-29, RN07 — list, read, items and writes are bounded by the servidor's grupos."""
    odonto = grupo(application, gestor, name=unique("MATERIAL ODONTOLÓGICO"))
    restauradores = grupo(application, gestor, parent=odonto["id"])
    expediente = grupo(application, gestor, name=unique("MATERIAL DE EXPEDIENTE"))
    mine = make_insumo(application, gestor, restauradores["id"])
    theirs = make_insumo(application, gestor, expediente["id"])
    ata = make_ata(application, gestor)
    add_item(application, gestor, ata["id"], mine["id"])
    add_item(application, gestor, ata["id"], theirs["id"])
    servidor = scoped_servidor(application, create_user, gestor, odonto["id"])

    listed = application.get(INSUMOS, params={"size": 100}, headers=servidor).json()
    assert {i["id"] for i in listed["items"]} == {mine["id"]}
    hidden = application.get(f"{INSUMOS}/{theirs['id']}", headers=servidor)
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "NOT_FOUND"
    items = application.get(f"{ATAS}/{ata['id']}/itens", headers=servidor).json()
    assert [i["insumo"]["id"] for i in items["items"]] == [mine["id"]]

    into_theirs = application.post(INSUMOS, json=insumo_body(expediente["id"]), headers=servidor)
    assert into_theirs.status_code == 422
    assert "grupo_id" in into_theirs.json()["error"]["fields"]
    moved = application.patch(
        f"{INSUMOS}/{mine['id']}", json={"grupo_id": expediente["id"]}, headers=servidor
    )
    assert moved.status_code == 422

    for unscoped in (gestor, auditor):
        assert application.get(f"{INSUMOS}/{theirs['id']}", headers=unscoped).status_code == 200
        both = application.get(f"{ATAS}/{ata['id']}/itens", headers=unscoped).json()
        assert len(both["items"]) == 2


def test_ac_0003_29_rn07_a_servidor_with_no_grupos_sees_nothing(
    application: TestClient, create_user: Callable[..., User], gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-29, RN07 — the list is empty, and so is the grupo tree."""
    make_insumo(application, gestor, raiz["id"])
    servidor = login(application, create_user, "servidor")[0]

    listed = application.get(INSUMOS, headers=servidor).json()

    assert listed == {"items": [], "total": 0, "page": 1, "size": 25}
    assert application.get(GRUPOS, headers=servidor).json() == []


def test_ac_0003_30_a_gestor_sets_a_servidors_grupos(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    db_session: Session,
) -> None:
    """AC-0003-30 — the set is replaced, applies at once, and the audit keeps the prior one."""
    first = grupo(application, gestor)
    second = grupo(application, gestor)
    third = grupo(application, gestor)
    servidor, user = login(application, create_user, "servidor")
    route = f"/api/v1/usuarios/{user.id}/grupos-materiais"
    application.post(route, json={"grupo_ids": [first["id"]]}, headers=gestor)
    in_third = make_insumo(application, gestor, third["id"])

    response = application.post(
        route, json={"grupo_ids": [second["id"], third["id"]]}, headers=gestor
    )

    assert response.status_code == 200, response.text
    assert set(response.json()["grupo_ids"]) == {second["id"], third["id"]}
    assert application.get(f"{INSUMOS}/{in_third['id']}", headers=servidor).status_code == 200
    rows = audit_rows(db_session, str(user.id), "usuario.grupos_alterados")
    assert rows[-1].dados_anteriores == {"grupos": [first["id"]]}


def test_ac_0003_32_a_gestor_reads_a_servidors_grupos(
    application: TestClient, create_user: Callable[..., User], gestor: dict[str, str]
) -> None:
    """AC-0003-32 — the stored set, without the grupos below it; 404 and 403 as stated."""
    first = grupo(application, gestor)
    below = grupo(application, gestor, parent=first["id"])
    second = grupo(application, gestor)
    servidor, user = login(application, create_user, "servidor")
    auditor, _ = login(application, create_user, "auditor")
    route = f"/api/v1/usuarios/{user.id}/grupos-materiais"
    application.post(route, json={"grupo_ids": [first["id"], second["id"]]}, headers=gestor)

    response = application.get(route, headers=gestor)

    assert response.status_code == 200, response.text
    assert set(response.json()["grupo_ids"]) == {first["id"], second["id"]}
    assert below["id"] not in response.json()["grupo_ids"]
    missing = application.get(f"/api/v1/usuarios/{uuid.uuid4()}/grupos-materiais", headers=gestor)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    for headers in (servidor, auditor):
        refused = application.get(route, headers=headers)
        assert refused.status_code == 403
        assert refused.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"


def test_ac_0003_30_only_a_servidor_has_grupos(
    application: TestClient, create_user: Callable[..., User], gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-30 — 422 for a gestor or an auditor; 403 when a servidor tries it."""
    for perfil in ("gestor", "auditor"):
        _, member = login(application, create_user, perfil)
        response = application.post(
            f"/api/v1/usuarios/{member.id}/grupos-materiais",
            json={"grupo_ids": [raiz["id"]]},
            headers=gestor,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_DATA"

    servidor, user = login(application, create_user, "servidor")
    refused = application.post(
        f"/api/v1/usuarios/{user.id}/grupos-materiais",
        json={"grupo_ids": [raiz["id"]]},
        headers=servidor,
    )
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"


# ── AC-0003-31 — audit in the same transaction ──────────────────────────────


def test_ac_0003_31_an_insumo_whose_audit_row_fails_is_not_saved(
    application: TestClient,
    gestor: dict[str, str],
    raiz: dict,
    create_user: Callable[..., User],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-0003-31 — if the history cannot be written, the insumo does not exist."""
    from app.services import insumos

    actor = create_user(perfil="gestor")
    code = sku()

    def broken(*args: object, **kwargs: object) -> None:
        raise RuntimeError("audit down")

    monkeypatch.setattr(insumos, "record", broken)
    with pytest.raises(RuntimeError):
        insumos.register(
            db_session,
            actor=db_session.get(User, actor.id),  # type: ignore[arg-type]
            sku=code,
            description="Objeto",
            unit="UN",
            grupo_id=uuid.UUID(raiz["id"]),
            codigo_doms=None,
            external_code=None,
            reference_quantity=None,
            at=datetime.datetime.now(datetime.UTC),
            correlation_id=uuid.uuid4(),
        )
    db_session.rollback()

    assert application.get(INSUMOS, params={"q": code}, headers=gestor).json()["total"] == 0


def test_ac_0003_35_a_text_field_holds_at_least_one_letter(
    application: TestClient, gestor: dict[str, str], raiz: dict
) -> None:
    """AC-0003-35 — by hand: a digit only SKU, descrição, unidade or grupo name is refused."""
    numeric = application.post(INSUMOS, json=insumo_body(raiz["id"], sku="123"), headers=gestor)
    assert numeric.status_code == 422
    assert numeric.json()["error"]["code"] == "INVALID_SKU"
    assert "ao menos uma letra" in numeric.json()["error"]["fields"]["sku"]

    digits = application.post(
        INSUMOS, json=insumo_body(raiz["id"], description="2", unit="3"), headers=gestor
    )
    assert digits.status_code == 422
    assert digits.json()["error"]["code"] == "INVALID_DATA"
    assert digits.json()["error"]["fields"] == {
        "description": "Use ao menos uma letra.",
        "unit": "Use ao menos uma letra.",
    }

    insumo = make_insumo(application, gestor, raiz["id"])
    edited = application.patch(f"{INSUMOS}/{insumo['id']}", json={"unit": "12"}, headers=gestor)
    assert edited.status_code == 422
    assert edited.json()["error"]["fields"] == {"unit": "Use ao menos uma letra."}

    for body in ({"name": "67", "parent_id": None}, {"name": "4", "parent_id": raiz["id"]}):
        refused = application.post(GRUPOS, json=body, headers=gestor)
        assert refused.status_code == 422
        assert refused.json()["error"]["fields"] == {"name": "Use ao menos uma letra."}
    renamed = application.patch(f"{GRUPOS}/{raiz['id']}", json={"name": "5"}, headers=gestor)
    assert renamed.status_code == 422
