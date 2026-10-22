"""The catalogue file and the items file — SPEC-0003 v1.1 AC-0003-06 to -08, -18, -19, -26.

Also SPEC-0001 AC-0001-42 v1.10: the two import routes take a body past 64 KiB.
"""

from __future__ import annotations

import decimal
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.catalogue import (
    ATAS,
    CSV_HEADERS,
    GRUPOS,
    INSUMOS,
    add_item,
    audit_rows,
    csv,
    doms,
    grupo,
    item_of,
    login,
    make_ata,
    make_insumo,
    new_cnpj,
    sku,
    unique,
)

IMPORT = f"{INSUMOS}/importacao"
HEADER = "sku;descricao;unidade;grupo;subgrupo;classificacao;codigo_doms;quantidade_referencia"


@pytest.fixture
def gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in gestor."""
    return login(application, create_user, "gestor")[0]


def send(
    application: TestClient,
    headers: dict[str, str],
    content: bytes,
    *,
    route: str = IMPORT,
    dry_run: bool = False,
) -> object:
    """Post a CSV file as the request body."""
    return application.post(
        route,
        content=content,
        params={"dry_run": "true"} if dry_run else None,
        headers={**headers, **CSV_HEADERS},
    )


def found(application: TestClient, headers: dict[str, str], code: str) -> list[dict]:
    """The insumos a search for `code` returns."""
    return application.get(INSUMOS, params={"q": code}, headers=headers).json()["items"]


# ── AC-0003-06 — the catalogue file ─────────────────────────────────────────


def test_ac_0003_06_a_gestor_imports_the_catalogue(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0003-06 — rows create or update by SKU, the grupo path is found or created."""
    existing = make_insumo(application, gestor, grupo(application, gestor)["id"], unit="UN")
    top, sub, leaf = unique("ODONTO"), unique("RESTAURADORES"), unique("RESINAS")
    new_sku, code = sku(), doms()

    response = send(
        application,
        gestor,
        csv(
            HEADER,
            f"{new_sku};RESINA A2;UN;{top};{sub};{leaf};{code};1.000",
            f"{existing['sku']};{existing['description']};CX;{top};;;;",
        ),
    )

    assert response.status_code == 200, response.text  # type: ignore[attr-defined]
    report = response.json()  # type: ignore[attr-defined]
    assert (report["created"], report["updated"], report["unchanged"]) == (1, 1, 0)
    created = found(application, gestor, new_sku)[0]
    assert [g["name"] for g in created["grupo_path"]] == [top, sub, leaf]
    assert created["codigo_doms"] == code
    assert decimal.Decimal(created["reference_quantity"]) == 1000
    updated = found(application, gestor, existing["sku"])[0]
    assert updated["unit"] == "CX"
    assert [g["name"] for g in updated["grupo_path"]] == [top]
    created_rows = audit_rows(db_session, created["id"], "insumo.criado")
    assert created_rows[0].justificativa == "Importado de arquivo CSV."
    assert (
        audit_rows(db_session, existing["id"], "insumo.editado")[0].dados_anteriores["unidade"]
        == "UN"
    )


def test_ac_0003_06_an_unknown_column_is_ignored_and_estoque_is_explained(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-06 — estoque and minimo are named; the stock column is said to go elsewhere."""
    response = send(
        application,
        gestor,
        csv(
            "sku;descricao;unidade;grupo;estoque;minimo",
            f"{sku()};LUVA M;CX;{unique('EPI')};250;10",
        ),
    )

    assert response.status_code == 200, response.text  # type: ignore[attr-defined]
    report = response.json()  # type: ignore[attr-defined]
    assert report["ignored_columns"] == ["estoque", "minimo"]
    assert any("cobertura" in note for note in report["notes"])


@pytest.mark.parametrize("missing", ["sku", "descricao", "unidade", "grupo"])
def test_ac_0003_06_a_row_without_a_required_cell_is_refused_by_line(
    application: TestClient, gestor: dict[str, str], missing: str
) -> None:
    """AC-0003-06 — the file is refused and the report names the line and the column."""
    cells = {"sku": sku(), "descricao": "LUVA", "unidade": "CX", "grupo": unique("EPI")}
    cells[missing] = ""
    row = ";".join(cells[c] for c in ("sku", "descricao", "unidade", "grupo"))

    response = send(application, gestor, csv("sku;descricao;unidade;grupo", row))

    assert response.status_code == 422  # type: ignore[attr-defined]
    error = response.json()["error"]  # type: ignore[attr-defined]
    assert error["code"] == "IMPORT_REJECTED"
    assert {"line": 2, "field": missing, "message": "Campo obrigatório."} in error["rows"]


def test_ac_0003_06_a_classificacao_needs_a_subgrupo(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-06 — a third level with no second refuses the line."""
    response = send(application, gestor, csv(HEADER, f"{sku()};X;UN;{unique('G')};;FOLHA;;"))

    assert response.status_code == 422  # type: ignore[attr-defined]
    rows = response.json()["error"]["rows"]  # type: ignore[attr-defined]
    assert rows[0]["field"] == "classificacao"


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0003_06_only_a_gestor_imports(
    application: TestClient, create_user: Callable[..., User], perfil: str
) -> None:
    """AC-0003-06 — 403 for a servidor and for an auditor."""
    headers = login(application, create_user, perfil)[0]

    response = send(application, headers, csv(HEADER))

    assert response.status_code == 403  # type: ignore[attr-defined]
    assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"  # type: ignore[attr-defined]


# ── AC-0003-07, -08 — all or nothing, dry run, repeatable ───────────────────


def test_ac_0003_07_an_import_is_all_or_nothing(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-07 — every invalid line is reported, not only the first, and nothing is written."""
    good, bad_sku = sku(), sku()
    lines = [HEADER] + [f"{sku()};ITEM {n};UN;{unique('G')};;;;" for n in range(8)]
    lines[3] = f"{good};BOM;UN;{unique('G')};;;;"
    lines[4] = f"{bad_sku};;UN;{unique('G')};;;;"
    lines[8] = "COM-HIFEN;RUIM;UN;G;;;;"

    response = send(application, gestor, csv(*lines))

    assert response.status_code == 422  # type: ignore[attr-defined]
    error = response.json()["error"]  # type: ignore[attr-defined]
    assert error["code"] == "IMPORT_REJECTED"
    assert {(r["line"], r["field"]) for r in error["rows"]} == {(5, "descricao"), (9, "sku")}
    assert found(application, gestor, good) == []


def test_ac_0003_07_a_dry_run_reports_and_writes_nothing(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0003-07 — the same report, nothing written, grupos included; invalid stays refused."""
    new, top = sku(), unique("SECO")

    response = send(application, gestor, csv(HEADER, f"{new};X;UN;{top};;;;"), dry_run=True)
    invalid = send(application, gestor, csv(HEADER, f"{new};;UN;{top};;;;"), dry_run=True)

    assert response.status_code == 200, response.text  # type: ignore[attr-defined]
    report = response.json()  # type: ignore[attr-defined]
    assert (report["created"], report["dry_run"]) == (1, True)
    assert found(application, gestor, new) == []
    tree = application.get(GRUPOS, headers=gestor).json()
    assert top not in {node["name"] for node in tree}
    assert invalid.status_code == 422  # type: ignore[attr-defined]


def test_ac_0003_08_an_import_can_be_repeated(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0003-08 — unchanged rows count as such and write no audit row; an empty cell keeps."""
    new, code, top = sku(), doms(), unique("REPETE")
    content = csv(HEADER, f"{new};GAZE;PCT;{top};;;{code};50")
    assert send(application, gestor, content).status_code == 200  # type: ignore[attr-defined]
    insumo = found(application, gestor, new)[0]

    again = send(application, gestor, content)
    emptier = send(application, gestor, csv(HEADER, f"{new};GAZE;PCT;{top};;;;"))

    assert again.json()["unchanged"] == 1  # type: ignore[attr-defined]
    assert emptier.json()["unchanged"] == 1  # type: ignore[attr-defined]
    kept = found(application, gestor, new)[0]
    assert (kept["codigo_doms"], decimal.Decimal(kept["reference_quantity"])) == (code, 50)
    assert len(found(application, gestor, new)) == 1
    assert len(audit_rows(db_session, insumo["id"])) == 1


def test_ac_0003_08_a_doms_code_of_another_sku_refuses_the_line(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-08 — a code already held by another insumo, or twice in the file, is a line."""
    code = doms()
    holder = make_insumo(application, gestor, grupo(application, gestor)["id"], codigo_doms=code)
    twice = doms()

    response = send(
        application,
        gestor,
        csv(
            HEADER,
            f"{sku()};A;UN;{unique('G')};;;{code};",
            f"{sku()};B;UN;{unique('G')};;;{twice};",
            f"{sku()};C;UN;{unique('G')};;;{twice};",
        ),
    )

    rows = response.json()["error"]["rows"]  # type: ignore[attr-defined]
    assert any(r["line"] == 2 and holder["sku"] in r["message"] for r in rows)
    assert any(r["line"] == 4 and r["field"] == "codigo_doms" for r in rows)


# ── AC-0003-18, -19 — the format and the measured hazards ───────────────────


def test_ac_0003_18_numbers_follow_the_separator(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-18 — `1.234,5` in a `;` file, `1234.5` in a `,` file, both 1234.5."""
    br, plain = sku(), sku()

    send(application, gestor, csv(HEADER, f"{br};A;UN;{unique('G')};;;;1.234,5"))
    send(
        application,
        gestor,
        csv(
            "sku,descricao,unidade,grupo,quantidade_referencia",
            f"{plain},B,UN,{unique('G')},1234.5",
        ),
    )

    for code in (br, plain):
        value = found(application, gestor, code)[0]["reference_quantity"]
        assert decimal.Decimal(value) == decimal.Decimal("1234.5")


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp1252"])
def test_ac_0003_18_accents_read_in_every_accepted_encoding(
    application: TestClient, gestor: dict[str, str], encoding: str
) -> None:
    """AC-0003-18 — UTF-8 with or without a BOM, and Windows-1252."""
    code = sku()

    response = send(
        application,
        gestor,
        csv(HEADER, f"{code};SOLUÇÃO FISIOLÓGICA;UN;{unique('SAÚDE')};;;;", encoding=encoding),
    )

    assert response.status_code == 200, response.text  # type: ignore[attr-defined]
    assert found(application, gestor, code)[0]["description"] == "SOLUÇÃO FISIOLÓGICA"


@pytest.mark.parametrize(
    "content",
    [
        b"\x00\x01\x02binario",
        b"\x81\x8d\x8f\x90\x9d",
        b"",
        b"sku;descricao;unidade\r\nX;Y;Z\r\n",
    ],
    ids=["binary", "not-an-encoding", "empty", "missing-column"],
)
def test_ac_0003_18_an_unreadable_file_is_refused(
    application: TestClient, gestor: dict[str, str], content: bytes
) -> None:
    """AC-0003-18 — 422 INVALID_FILE, nothing written."""
    response = send(application, gestor, content)

    assert response.status_code == 422  # type: ignore[attr-defined]
    assert response.json()["error"]["code"] == "INVALID_FILE"  # type: ignore[attr-defined]


def test_ac_0003_18_too_many_lines_is_refused(
    application: TestClient, gestor: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-0003-18 — past `import_max_lines` the file is refused whole."""
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "import_max_lines", 2)
    lines = [HEADER] + [f"{sku()};X;UN;{unique('G')};;;;" for _ in range(3)]

    response = send(application, gestor, csv(*lines))

    assert response.status_code == 422  # type: ignore[attr-defined]
    assert response.json()["error"]["code"] == "INVALID_FILE"  # type: ignore[attr-defined]


def test_ac_0001_42_the_import_routes_take_a_body_past_64_kib(
    application: TestClient, gestor: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-0001-42 v1.10 — 64 KiB passes on an import route, `import_max_bytes` does not."""
    from app.core.config import get_settings

    top = unique("VOLUME")
    lines = [HEADER] + [f"{sku()};{'X' * 200};UN;{top};;;;" for _ in range(400)]
    content = csv(*lines)
    assert len(content) > 64 * 1024

    accepted = send(application, gestor, content, dry_run=True)
    monkeypatch.setattr(get_settings(), "import_max_bytes", 70 * 1024)
    refused = send(application, gestor, content + b"x" * (10 * 1024), dry_run=True)
    elsewhere = application.post(
        INSUMOS, content=b"{" + b" " * (65 * 1024) + b"}", headers={**gestor, **CSV_HEADERS}
    )

    assert accepted.status_code == 200, accepted.text  # type: ignore[attr-defined]
    assert refused.status_code == 413  # type: ignore[attr-defined]
    assert elsewhere.status_code == 413


def test_ac_0003_19_the_hazards_of_the_source_files_are_caught(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-19 — spaces trimmed, the DOMS code lifted out of the descrição, floats refused."""
    spaced, lifted, kept = sku(), sku(), sku()
    code, same = doms(), doms()

    response = send(
        application,
        gestor,
        csv(
            HEADER,
            f"  {spaced} ;  LUVA M  ; CX ; {unique('EPI')} ;;;;",
            f"{lifted};{code} - CLOREXIDINA 2% - 1 L;UN;{unique('G')};;;;",
            f"{kept};{same} - SORO;UN;{unique('G')};;;{same};",
        ),
    )

    assert response.status_code == 200, response.text  # type: ignore[attr-defined]
    assert response.json()["corrected_descriptions"] == 2  # type: ignore[attr-defined]
    assert found(application, gestor, spaced)[0]["description"] == "LUVA M"
    lifted_row = found(application, gestor, lifted)[0]
    assert (lifted_row["description"], lifted_row["codigo_doms"]) == (
        "CLOREXIDINA 2% - 1 L",
        code,
    )
    assert found(application, gestor, kept)[0]["description"] == "SORO"


def test_ac_0003_19_a_float_code_or_a_contradicting_code_refuses_the_line(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-19 — `2888.0` is refused, and so is a descrição whose code is not the column's."""
    response = send(
        application,
        gestor,
        csv(
            "sku;descricao;unidade;grupo;codigo_doms;codigo_externo",
            f"{sku()};A;UN;{unique('G')};2888.0;",
            f"{sku()};B;UN;{unique('G')};;3678.0",
            f"{sku()};26829 - C;UN;{unique('G')};11111;",
        ),
    )

    rows = response.json()["error"]["rows"]  # type: ignore[attr-defined]
    assert {(r["line"], r["field"]) for r in rows} == {
        (2, "codigo_doms"),
        (3, "codigo_externo"),
        (4, "descricao"),
    }


# ── AC-0003-26 — the items file ─────────────────────────────────────────────

ITEMS_HEADER = "sku;quantidade;valor_unitario;numero_item;cnpj_fornecedor;razao_social_fornecedor"


def test_ac_0003_26_a_gestor_imports_an_atas_items(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0003-26 — added, corrected, unchanged; an item not in the file is left alone."""
    other = new_cnpj()
    raiz = grupo(application, gestor)
    a, b, c, d = (make_insumo(application, gestor, raiz["id"]) for _ in range(4))
    ata = make_ata(application, gestor)
    add_item(application, gestor, ata["id"], b["id"], quantity="10", unit_price="2")
    add_item(application, gestor, ata["id"], c["id"], quantity="5", unit_price="3")
    add_item(application, gestor, ata["id"], d["id"], quantity="7", unit_price="1")

    response = send(
        application,
        gestor,
        csv(
            ITEMS_HEADER,
            f"{a['sku']};1.000;R$ 0,00599;1;{other};Distribuidora B Ltda",
            f"{b['sku']};12;2;2;;",
            f"{c['sku'].lower()};5;3;;;",
        ),
        route=f"{ATAS}/{ata['id']}/itens/importacao",
    )

    assert response.status_code == 200, response.text  # type: ignore[attr-defined]
    report = response.json()  # type: ignore[attr-defined]
    assert (report["added"], report["corrected"], report["unchanged"]) == (1, 1, 1)
    items = application.get(f"{ATAS}/{ata['id']}/itens", headers=gestor).json()
    new = item_of(items, a["id"])
    assert decimal.Decimal(new["unit_price"]) == decimal.Decimal("0.00599")
    assert decimal.Decimal(new["total_value"]) == decimal.Decimal("5.99")
    assert new["fornecedor"]["cnpj"] == other
    assert decimal.Decimal(item_of(items, b["id"])["quantity"]) == 12
    assert decimal.Decimal(item_of(items, d["id"])["quantity"]) == 7
    assert len(audit_rows(db_session, ata["id"], "ata.item_editado")) == 1


def test_ac_0003_26_the_items_file_creates_no_insumo(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-26 — unknown, discontinued and repeated SKUs are lines to fix."""
    raiz = grupo(application, gestor)
    gone = make_insumo(application, gestor, raiz["id"])
    twice = make_insumo(application, gestor, raiz["id"])
    application.post(
        f"{INSUMOS}/{gone['id']}/descontinuar", json={"justification": "Fora."}, headers=gestor
    )
    ata = make_ata(application, gestor)
    unknown = sku()

    response = send(
        application,
        gestor,
        csv(
            ITEMS_HEADER,
            f"{unknown};1;1;;;",
            f"{gone['sku']};1;1;;;",
            f"{twice['sku']};1;1;;;",
            f"{twice['sku']};2;1;;;",
            f"{twice['sku'][:-1]}Z;1;1;;11.222.333/0001-00;",
        ),
        route=f"{ATAS}/{ata['id']}/itens/importacao",
    )

    assert response.status_code == 422  # type: ignore[attr-defined]
    rows = response.json()["error"]["rows"]  # type: ignore[attr-defined]
    lines = {(r["line"], r["field"]) for r in rows}
    assert {(2, "sku"), (3, "sku"), (4, "sku"), (5, "sku"), (6, "cnpj_fornecedor")} <= lines
    assert found(application, gestor, unknown) == []
    assert application.get(f"{ATAS}/{ata['id']}/itens", headers=gestor).json()["items"] == []


def test_ac_0003_26_a_new_fornecedor_needs_its_razao_social(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-26 — an unknown CNPJ with no razão social refuses the line."""
    insumo = make_insumo(application, gestor, grupo(application, gestor)["id"])
    ata = make_ata(application, gestor)

    response = send(
        application,
        gestor,
        csv(ITEMS_HEADER, f"{insumo['sku']};1;1;;{new_cnpj()};"),
        route=f"{ATAS}/{ata['id']}/itens/importacao",
    )

    rows = response.json()["error"]["rows"]  # type: ignore[attr-defined]
    assert rows == [
        {
            "line": 2,
            "field": "razao_social_fornecedor",
            "message": "Informe a razão social para um fornecedor novo.",
        }
    ]


def test_ac_0003_26_a_dry_run_writes_no_item(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-26 with AC-0003-07 — the report, and no item."""
    insumo = make_insumo(application, gestor, grupo(application, gestor)["id"])
    ata = make_ata(application, gestor)

    response = send(
        application,
        gestor,
        csv(ITEMS_HEADER, f"{insumo['sku']};10;1,5;;;"),
        route=f"{ATAS}/{ata['id']}/itens/importacao",
        dry_run=True,
    )

    assert response.json()["added"] == 1  # type: ignore[attr-defined]
    assert application.get(f"{ATAS}/{ata['id']}/itens", headers=gestor).json()["items"] == []


def test_ac_0003_26_a_closed_ata_takes_no_file(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-26 — the ATA must be vigente or suspensa, as for one item."""
    insumo = make_insumo(application, gestor, grupo(application, gestor)["id"])
    ata = make_ata(application, gestor)
    application.post(f"{ATAS}/{ata['id']}/encerrar", headers=gestor)

    response = send(
        application,
        gestor,
        csv(ITEMS_HEADER, f"{insumo['sku']};1;1;;;"),
        route=f"{ATAS}/{ata['id']}/itens/importacao",
    )

    assert response.status_code == 409  # type: ignore[attr-defined]
    assert response.json()["error"]["code"] == "ATA_NAO_EDITAVEL"  # type: ignore[attr-defined]


# ── AC-0003-33 — the report shows every line as it will be written ─────────


def test_ac_0003_33_the_catalogue_report_lists_every_line(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-33 — each line as stored, with its action, in a dry run and in the import."""
    top = unique("ODONTO")
    kept = make_insumo(application, gestor, grupo(application, gestor, name=top)["id"], unit="UN")
    changed = make_insumo(application, gestor, grupo(application, gestor)["id"], unit="UN")
    new_sku, code = sku(), doms()
    content = csv(
        HEADER,
        f" {new_sku.lower()} ;{code} - CLOREXIDINA 2% - 1 L;UN;{top};SUB;;;",
        f"{changed['sku']};{changed['description']};CX;{top};;;;",
        f"{kept['sku']};{kept['description']};UN;{top};;;;",
    )

    for dry_run in (True, False):
        response = send(application, gestor, content, dry_run=dry_run)
        assert response.status_code == 200, response.text  # type: ignore[attr-defined]
        lines = response.json()["lines"]  # type: ignore[attr-defined]
        assert [(line["line"], line["sku"], line["action"]) for line in lines] == [
            (2, new_sku, "created"),
            (3, changed["sku"], "updated"),
            (4, kept["sku"], "unchanged"),
        ]
        first = lines[0]
        assert first["description"] == "CLOREXIDINA 2% - 1 L"
        assert first["codigo_doms"] == code
        assert first["corrected_description"] is True
        assert first["grupo_path"] == [top, "SUB"]
        assert lines[1]["unit"] == "CX"


def test_ac_0003_33_the_items_report_lists_every_line(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-33 — each item line with the insumo's descrição, the values stored and its action."""
    other = new_cnpj()
    raiz = grupo(application, gestor)
    a, b = (make_insumo(application, gestor, raiz["id"]) for _ in range(2))
    ata = make_ata(application, gestor)
    add_item(application, gestor, ata["id"], b["id"], quantity="10", unit_price="2")

    response = send(
        application,
        gestor,
        csv(
            ITEMS_HEADER,
            f"{a['sku']};1.000;R$ 0,00599;7;{other};Distribuidora C Ltda",
            f"{b['sku']};10;2;;;",
        ),
        route=f"{ATAS}/{ata['id']}/itens/importacao",
        dry_run=True,
    )

    assert response.status_code == 200, response.text  # type: ignore[attr-defined]
    first, second = response.json()["lines"]  # type: ignore[attr-defined]
    assert (first["sku"], first["action"], first["item_number"]) == (a["sku"], "added", "7")
    assert first["description"] == a["description"]
    assert decimal.Decimal(first["quantity"]) == 1000
    assert decimal.Decimal(first["unit_price"]) == decimal.Decimal("0.00599")
    assert first["fornecedor"] == "Distribuidora C Ltda"
    assert (second["sku"], second["action"], second["fornecedor"]) == (b["sku"], "unchanged", None)


# ── AC-0003-34 — control characters and formulas are refused ───────────────


@pytest.mark.parametrize(
    ("cell", "message"),
    [
        ("CLOREXIDINA\tDEGERMANTE", "Caractere de controle não permitido."),
        ('"CLOREXIDINA\nDEGERMANTE"', "Caractere de controle não permitido."),
        ("CLOREXIDINA\x07", "Caractere de controle não permitido."),
        ('=HYPERLINK("http://exemplo")', "O texto não pode começar com =, + ou @."),
        ("+CLOREXIDINA", "O texto não pode começar com =, + ou @."),
        ("@SUM(A1)", "O texto não pode começar com =, + ou @."),
    ],
)
def test_ac_0003_34_a_control_character_or_a_formula_is_refused(
    application: TestClient, gestor: dict[str, str], cell: str, message: str
) -> None:
    """AC-0003-34 — the cell is named and nothing is written."""
    new_sku = sku()
    response = send(application, gestor, csv(HEADER, f"{new_sku};{cell};UN;{unique('G')};;;;"))

    assert response.status_code == 422, response.text  # type: ignore[attr-defined]
    body = response.json()["error"]  # type: ignore[attr-defined]
    assert body["code"] == "IMPORT_REJECTED"
    assert {"line": 2, "field": "descricao", "message": message} in body["rows"]
    assert found(application, gestor, new_sku) == []


def test_ac_0003_34_a_leading_minus_is_not_a_formula(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-34 — "-" stays allowed, because descrições start with it."""
    new_sku = sku()
    response = send(
        application, gestor, csv(HEADER, f"{new_sku};- LUVA DE PROCEDIMENTO;UN;{unique('G')};;;;")
    )

    assert response.status_code == 200, response.text  # type: ignore[attr-defined]
