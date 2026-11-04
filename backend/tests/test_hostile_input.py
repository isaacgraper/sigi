"""Hostile input on the write routes: code, formulas, overflow, control characters.

SIGI never evaluates what it is sent. A text field keeps code or a formula as
the literal characters typed; a number field refuses anything that is not a
number within its bounds; nothing here may answer 500. The bounds are
AC-0001-41's, the registrations AC-0002-01, AC-0003-01, AC-0003-06 and AC-0004-02.

The same payloads run once more against every screen in the final pass
(`docs/process/sop-qualidade.md`, "Hostile input").
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.models.user import User
from tests.catalogue import (
    ATAS,
    CSV_HEADERS,
    INSUMOS,
    add_item,
    csv,
    grupo,
    insumo_body,
    item_of,
    login,
    make_ata,
    make_insumo,
    sku,
    unique,
)

NES = "/api/v1/notas-empenho"
PROCESSO = "00301.000451/2026-12"
CATALOGUE_HEADER = (
    "sku;descricao;unidade;grupo;subgrupo;classificacao;codigo_doms;quantidade_referencia"
)

CODE = [
    "Function('return process')()",
    "new Function('alert(1)')()",
    "lambda: __import__('os').system('id')",
    "eval('1+1')",
    "exec('import os; os.remove(\"/\")')",
    "__import__('subprocess').call(['ls'])",
    "require('child_process').exec('id')",
    "constructor.constructor('return this')()",
    "${7*7}",
    "{{7*7}}",
    "#{7*7}",
    "<%= 7*7 %>",
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert(1)",
    "'; DROP TABLE insumo; --",
    "' OR '1'='1",
    "$(rm -rf ~)",
    "`id`",
    "../../etc/passwd",
]

FORMULAS = [
    "=1+1",
    "=cmd|' /C calc'!A0",
    '=HYPERLINK("http://example.com","clique")',
    "+SUM(1,1)",
    "-2+3",
    "@SUM(1,1)",
    "=IMPORTXML(A1,B1)",
]

UNICODE = ["Luva 🧤 nitrílica", "Ácido ﷽ 𝓧", "‮LUVA", "ＳＯＲＯ"]

NOT_A_NUMBER = [
    "abc",
    "NaN",
    "nan",
    "Infinity",
    "-Infinity",
    "inf",
    "1e400",
    "0x10",
    "1,5,5",
    "eval('1')",
    "lambda: 1",
    "Function('return 1')()",
    "",
    " ",
    "--1",
]

CONTROL = ["LUVA\x00M", "\x00", "LUVA\x07M", "LUVA\x1bM"]


@pytest.fixture
def gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in gestor."""
    return login(application, create_user, "gestor")[0]


@pytest.fixture
def raiz(application: TestClient, gestor: dict[str, str]) -> dict:
    """A nivel 1 grupo of this test's own."""
    return grupo(application, gestor)


# ── Text fields keep code and formulas literally ────────────────────────────


# A description needs a letter (AC-0003-01), so a payload with none is refused there.
LETTERED = [value for value in CODE + FORMULAS + UNICODE if any(c.isalpha() for c in value)]
UNLETTERED = [value for value in CODE + FORMULAS if not any(c.isalpha() for c in value)]


@pytest.mark.parametrize("value", LETTERED)
def test_ac_0003_01_code_in_a_description_is_kept_as_text(
    application: TestClient, gestor: dict[str, str], raiz: dict, value: str
) -> None:
    """AC-0003-01 — the insumo stores the characters, and nothing evaluates them."""
    created = make_insumo(application, gestor, raiz["id"], description=value)
    assert created["description"] == value.strip()

    read = application.get(f"{INSUMOS}/{created['id']}", headers=gestor)
    assert read.status_code == 200, read.text
    assert read.json()["description"] == value.strip()


@pytest.mark.parametrize("value", UNLETTERED)
def test_ac_0003_01_a_description_without_a_letter_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict, value: str
) -> None:
    """AC-0003-01 — `${7*7}` names no material, so it is refused, not evaluated."""
    response = application.post(
        INSUMOS, json=insumo_body(raiz["id"], description=value), headers=gestor
    )
    assert response.status_code == 422, response.text
    assert "description" in response.json()["error"]["fields"]


@pytest.mark.parametrize("value", CODE + FORMULAS)
def test_ac_0002_01_code_in_an_ata_is_kept_as_text(
    application: TestClient, gestor: dict[str, str], value: str
) -> None:
    """AC-0002-01 — objeto, órgão and razão social store the characters as typed."""
    ata = make_ata(
        application,
        gestor,
        subject=value,
        organ=value[:200],
        fornecedor={"cnpj": "11.222.333/0001-81", "legal_name": value[:200]},
    )

    read = application.get(f"{ATAS}/{ata['id']}", headers=gestor)
    assert read.status_code == 200, read.text
    body = read.json()
    assert (body["subject"], body["organ"]) == (value.strip(), value[:200].strip())


# The importer refuses a cell a spreadsheet would run (AC-0003-06), and the
# description still needs a letter; whatever passes both is kept as typed.
IMPORTED = [value for value in LETTERED if not value.startswith(("=", "+", "@"))]
NOT_IMPORTED = [value for value in CODE + FORMULAS if value not in IMPORTED]


@pytest.mark.parametrize("value", [value for value in IMPORTED if value in CODE])
def test_ac_0003_06_code_in_the_catalogue_file_is_kept_as_text(
    application: TestClient, gestor: dict[str, str], value: str
) -> None:
    """AC-0003-06 — a cell that looks like code is imported as its text, never run."""
    code = sku()
    description = value.replace(";", ",")

    response = application.post(
        f"{INSUMOS}/importacao",
        content=csv(CATALOGUE_HEADER, f"{code};{description};UN;{unique('G')};;;;"),
        headers={**gestor, **CSV_HEADERS},
    )

    assert response.status_code == 200, response.text
    listed = application.get(INSUMOS, params={"q": code}, headers=gestor).json()["items"]
    assert [row["description"] for row in listed] == [description.strip()]


@pytest.mark.parametrize("value", NOT_IMPORTED)
def test_ac_0003_06_a_formula_in_the_catalogue_file_refuses_its_line(
    application: TestClient, gestor: dict[str, str], value: str
) -> None:
    """AC-0003-06 — a formula, or a cell with no letter, refuses its line on descricao."""
    response = application.post(
        f"{INSUMOS}/importacao",
        content=csv(CATALOGUE_HEADER, f"{sku()};{value.replace(';', ',')};UN;{unique('G')};;;;"),
        headers={**gestor, **CSV_HEADERS},
    )

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "IMPORT_REJECTED"
    assert {row["field"] for row in error["rows"]} == {"descricao"}


@pytest.mark.parametrize("value", ["=1+1", "lambda: 1", "eval('5')", "NaN", "1e400"])
def test_ac_0003_06_a_formula_in_a_number_cell_refuses_its_line(
    application: TestClient, gestor: dict[str, str], value: str
) -> None:
    """AC-0003-06 — quantidade_referencia that is not a number refuses the line, never 500."""
    response = application.post(
        f"{INSUMOS}/importacao",
        content=csv(CATALOGUE_HEADER, f"{sku()};SORO;UN;{unique('G')};;;;{value}"),
        headers={**gestor, **CSV_HEADERS},
    )

    assert response.status_code == 422, response.text


# ── Number fields refuse anything that is not a bounded number ──────────────


@pytest.mark.parametrize("value", NOT_A_NUMBER)
def test_ac_0002_04_an_ata_valor_that_is_not_a_number_is_refused(
    application: TestClient, gestor: dict[str, str], value: str
) -> None:
    """AC-0002-04 — the valor total is named, and no ATA is written."""
    number = f"ATA-{unique('X').replace(' ', '')}"
    response = application.post(
        ATAS,
        json={
            "number": number,
            "subject": "Teste",
            "organ": "SES",
            "fornecedor": {"cnpj": "11.222.333/0001-81", "legal_name": "Fornecedor"},
            "vigencia_inicio": "2026-01-01",
            "vigencia_fim": "2026-12-31",
            "total_value": value,
            "budget_date": "2026-03-10",
        },
        headers=gestor,
    )

    assert response.status_code == 422, response.text
    assert "total_value" in response.json()["error"]["fields"]


@pytest.mark.parametrize("value", NOT_A_NUMBER)
@pytest.mark.parametrize("field", ["quantity", "unit_price"])
def test_ac_0003_10_an_item_number_that_is_not_a_number_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict, field: str, value: str
) -> None:
    """AC-0003-10 — quantity and unit_price of an ATA's item are named."""
    ata = make_ata(application, gestor)
    insumo = make_insumo(application, gestor, raiz["id"])
    body = {"insumo_id": insumo["id"], "quantity": "10", "unit_price": "1.5", field: value}

    response = application.post(f"{ATAS}/{ata['id']}/itens", json=body, headers=gestor)

    assert response.status_code == 422, response.text
    assert field in response.json()["error"]["fields"]


@pytest.mark.parametrize("value", NOT_A_NUMBER)
def test_ac_0004_02_an_ne_quantity_that_is_not_a_number_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict, value: str
) -> None:
    """AC-0004-02 — the quantity is named on its line, and no NE is opened."""
    ata = make_ata(application, gestor)
    insumo = make_insumo(application, gestor, raiz["id"])
    item = item_of(add_item(application, gestor, ata["id"], insumo["id"]), insumo["id"])

    response = application.post(
        NES,
        json={
            "ata_id": ata["id"],
            "processo_sei": PROCESSO,
            "items": [{"item_ata_id": item["id"], "quantity": value}],
        },
        headers=gestor,
    )

    assert response.status_code == 422, response.text
    assert "items.0.quantity" in response.json()["error"]["fields"]


@pytest.mark.parametrize("value", [True, [1], {"a": 1}, 1e308, -1e308])
def test_ac_0004_02_an_ne_quantity_of_another_json_type_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict, value: object
) -> None:
    """AC-0004-02 — a boolean, a list, an object or a float past the bounds is refused."""
    ata = make_ata(application, gestor)
    insumo = make_insumo(application, gestor, raiz["id"])
    item = item_of(add_item(application, gestor, ata["id"], insumo["id"]), insumo["id"])

    response = application.post(
        NES,
        json={
            "ata_id": ata["id"],
            "processo_sei": PROCESSO,
            "items": [{"item_ata_id": item["id"], "quantity": value}],
        },
        headers=gestor,
    )

    assert response.status_code == 422, response.text


@pytest.mark.parametrize("value", ["lambda: 1", "eval('1')", "1e400", "NaN", "-1"])
def test_ac_0003_01_a_reference_quantity_that_is_not_a_number_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict, value: str
) -> None:
    """AC-0003-01 — quantidade de referência is named."""
    response = application.post(
        INSUMOS, json=insumo_body(raiz["id"], reference_quantity=value), headers=gestor
    )

    assert response.status_code == 422, response.text
    assert "reference_quantity" in response.json()["error"]["fields"]


# ── Identifiers and lengths ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value", ["eval('1')", "1 OR 1=1", "../../etc/passwd", "00000000-0000-0000-0000-00000000000g"]
)
def test_ac_0004_02_an_ata_id_that_is_not_a_uuid_is_refused(
    application: TestClient, gestor: dict[str, str], value: str
) -> None:
    """AC-0004-02 — an identifier that is not a UUID is named, never looked up."""
    response = application.post(
        NES, json={"ata_id": value, "processo_sei": PROCESSO, "items": []}, headers=gestor
    )

    assert response.status_code == 422, response.text
    assert "ata_id" in response.json()["error"]["fields"]


@pytest.mark.parametrize("path", ["eval('1')", "1%20OR%201=1", "..%2F..%2Fetc%2Fpasswd"])
def test_ac_0004_02_a_path_id_that_is_not_a_uuid_is_refused(
    application: TestClient, gestor: dict[str, str], path: str
) -> None:
    """A route identifier that is not a UUID is refused, not looked up."""
    response = application.get(f"{NES}/{path}", headers=gestor)
    assert response.status_code in (404, 422), response.text


@pytest.mark.parametrize(("field", "limit"), [("sku", 40), ("description", 300), ("unit", 20)])
def test_ac_0001_41_an_overlong_insumo_field_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict, field: str, limit: int
) -> None:
    """AC-0001-41 — one character past the column is named, never truncated."""
    value = "A" * (limit + 1)
    response = application.post(
        INSUMOS, json=insumo_body(raiz["id"], **{field: value}), headers=gestor
    )

    assert response.status_code == 422, response.text
    assert field in response.json()["error"]["fields"]


@pytest.mark.parametrize(("field", "limit"), [("number", 60), ("organ", 200)])
def test_ac_0001_41_an_overlong_ata_field_is_refused(
    application: TestClient, gestor: dict[str, str], field: str, limit: int
) -> None:
    """AC-0001-41 — the ATA's bounded texts are named past their column."""
    response = application.post(
        ATAS,
        json={
            "number": f"ATA-{unique('L').replace(' ', '')}",
            "subject": "Teste",
            "organ": "SES",
            "fornecedor": {"cnpj": "11.222.333/0001-81", "legal_name": "Fornecedor"},
            "vigencia_inicio": "2026-01-01",
            "vigencia_fim": "2026-12-31",
            "total_value": "10.00",
            "budget_date": "2026-03-10",
            field: "A" * (limit + 1),
        },
        headers=gestor,
    )

    assert response.status_code == 422, response.text
    assert field in response.json()["error"]["fields"]


# ── Control characters ──────────────────────────────────────────────────────


@pytest.mark.parametrize("value", CONTROL)
def test_ac_0001_41_a_control_character_is_refused(
    application: TestClient, gestor: dict[str, str], raiz: dict, value: str
) -> None:
    """AC-0001-41 — a NUL or another control character is named, never a 500."""
    response = application.post(
        INSUMOS, json=insumo_body(raiz["id"], description=value), headers=gestor
    )

    assert response.status_code == 422, response.text
    assert "description" in response.json()["error"]["fields"]


@pytest.mark.parametrize("value", CONTROL)
def test_ac_0001_41_a_control_character_in_an_ata_is_refused(
    application: TestClient, gestor: dict[str, str], value: str
) -> None:
    """AC-0001-41 — the same on an ATA's objeto, whose column has no length."""
    response = application.post(
        ATAS,
        json={
            "number": f"ATA-{unique('C').replace(' ', '')}",
            "subject": value,
            "organ": "SES",
            "fornecedor": {"cnpj": "11.222.333/0001-81", "legal_name": "Fornecedor"},
            "vigencia_inicio": "2026-01-01",
            "vigencia_fim": "2026-12-31",
            "total_value": "10.00",
            "budget_date": "2026-03-10",
        },
        headers=gestor,
    )

    assert response.status_code == 422, response.text
    assert "subject" in response.json()["error"]["fields"]


def test_ac_0003_06_a_nul_in_the_catalogue_file_is_refused(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0003-06 — a NUL in a cell refuses the file, never a 500."""
    response = application.post(
        f"{INSUMOS}/importacao",
        content=csv(CATALOGUE_HEADER, f"{sku()};LUVA\x00M;UN;{unique('G')};;;;"),
        headers={**gestor, **CSV_HEADERS},
    )

    assert response.status_code == 422, response.text
