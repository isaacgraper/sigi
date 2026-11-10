"""Reports and their exports — SPEC-0009 v1.1.

The gestor and the auditor export four reports as CSV and as PDF, every figure
read as it stood at the data de referência (AC-0009-03). The database is shared
by the suite, so each test reads its own ATA through `ata_id`.
"""

from __future__ import annotations

import csv
import datetime
import io
import time
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.constants import LOCAL_TIMEZONE
from app.core import clock
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services import relatorio_files
from app.services.errors import InvalidData
from app.services.relatorios import chosen, rewound
from tests.catalogue import login
from tests.test_notas_empenho import open_ne, setup_ata, to_stage
from tests.test_notas_fiscais import error, launched, moved

REPORTS = "/api/v1/relatorios"
HIST = "/api/v1/historico"
ATAS = "/api/v1/atas"
NES = "/api/v1/notas-empenho"
NAMES = (
    "execucao-orcamentaria",
    "posicao-saldo",
    "notas-fiscais-em-conferencia",
    "indicadores-fornecedores",
)
BOM = b"\xef\xbb\xbf"


@pytest.fixture
def gestor_user(application: TestClient, create_user: Callable[..., User]) -> tuple[dict, User]:
    """A signed-in gestor and its row."""
    return login(application, create_user, "gestor")


@pytest.fixture
def gestor(gestor_user: tuple[dict, User]) -> dict[str, str]:
    """Headers for a signed-in gestor."""
    return gestor_user[0]


@pytest.fixture
def servidor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in servidor."""
    return login(application, create_user, "servidor")[0]


@pytest.fixture
def auditor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in auditor."""
    return login(application, create_user, "auditor")[0]


@pytest.fixture
def cycle(application: TestClient, gestor: dict[str, str]) -> tuple[dict, list[dict], dict, dict]:
    """An ATA of 100.000,00, an NE of 3.000,00 issued on it and an NF of 1.000,00 launched."""
    ata, items = setup_ata(application, gestor, [("1000", "10"), ("500", "2")])
    created = open_ne(application, gestor, ata["id"], [(items[0]["id"], "300")])
    assert created.status_code == 201, created.text
    ne = to_stage(application, gestor, created.json()["id"], "ne_emitida")
    nf = launched(application, gestor, ne, "100", "1000.00")
    return ata, items, ne, nf


def read(
    application: TestClient, headers: dict[str, str], relatorio: str, **params: str
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """A report as CSV: its provenance and its rows by column. It must be served."""
    response = application.get(f"{REPORTS}/{relatorio}", params=params, headers=headers)
    assert response.status_code == 200, response.text
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
    gap = rows.index([])
    columns = rows[gap + 1]
    return (
        {row[0]: row[1] for row in rows[:gap]},
        [dict(zip(columns, row, strict=True)) for row in rows[gap + 2 :]],
    )


def instant() -> str:
    """Now, with a margin on both sides so no write shares the instant."""
    time.sleep(0.05)
    at = clock.now().isoformat()
    time.sleep(0.05)
    return at


# ── AC-0009-01 ─ four reports, two formats ───────────────────────────────────


@pytest.mark.parametrize("relatorio", NAMES)
@pytest.mark.parametrize(("formato", "opening"), [("csv", BOM), ("pdf", b"%PDF")])
def test_AC_0009_01_RF12_every_report_is_served_in_both_formats(
    application: TestClient,
    gestor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
    relatorio: str,
    formato: str,
    opening: bytes,
) -> None:
    """Each of the four reports downloads as CSV and as PDF."""
    response = application.get(
        f"{REPORTS}/{relatorio}",
        params={"formato": formato, "ata_id": cycle[0]["id"]},
        headers=gestor,
    )

    assert response.status_code == 200, response.text
    assert response.content.startswith(opening)
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment") and disposition.endswith(f'.{formato}"')
    assert relatorio in disposition


def test_AC_0009_01_an_unknown_report_is_not_found(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """A name that is none of the four answers 404."""
    response = application.get(f"{REPORTS}/desconhecido", headers=gestor)

    assert response.status_code == 404
    assert error(response)["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"formato": "xlsx"}, "formato"),
        ({"referencia": "2999-01-01T00:00:00+00:00"}, "referencia"),
        ({"referencia": "2026-01-01T00:00:00"}, "referencia"),
    ],
)
def test_AC_0009_01_a_wrong_parameter_is_refused_by_field(
    application: TestClient, gestor: dict[str, str], params: dict[str, str], field: str
) -> None:
    """An unknown format, a future reference and one with no offset answer 422."""
    response = application.get(f"{REPORTS}/posicao-saldo", params=params, headers=gestor)

    assert response.status_code == 422, response.text
    assert error(response)["code"] == "INVALID_DATA"
    assert field in error(response)["fields"]


def test_AC_0009_01_an_unknown_ata_is_not_found(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """A filter on an ATA that does not exist answers 404."""
    response = application.get(
        f"{REPORTS}/posicao-saldo", params={"ata_id": str(uuid.uuid4())}, headers=gestor
    )

    assert response.status_code == 404
    assert error(response)["code"] == "NOT_FOUND"


# ── AC-0009-02 ─ provenance ──────────────────────────────────────────────────


def test_AC_0009_02_an_export_opens_with_its_provenance(
    application: TestClient,
    gestor_user: tuple[dict, User],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """The file says what it is, who asked, when, at which reference and under which filter."""
    headers, user = gestor_user
    ata = cycle[0]
    reference = instant()

    header, _ = read(application, headers, "posicao-saldo", referencia=reference, ata_id=ata["id"])

    assert header["Relatório"] == "Posição de saldo consolidada"
    assert uuid.UUID(header["Identificador"])
    assert header["Gerado por"] == user.nome
    assert header["Data de referência"] == datetime.datetime.fromisoformat(reference).astimezone(
        LOCAL_TIMEZONE
    ).strftime("%d/%m/%Y %H:%M:%S")
    assert header["Gerado em"]
    assert header["Período"] == "Até a data de referência"
    assert header["Filtros"] == f"ATA: {ata['number']}"


def test_AC_0009_02_an_export_without_a_filter_says_so(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """With no filter the provenance reads Nenhum instead of an empty cell."""
    header, _ = read(application, gestor, "indicadores-fornecedores")

    assert header["Filtros"] == "Nenhum"


# ── AC-0009-03 ─ the same figures at the same reference ──────────────────────


def test_AC_0009_03_a_report_repeats_its_figures_after_the_data_changes(
    application: TestClient,
    gestor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """What changes after the reference leaves every report at that reference as it was."""
    ata, items, _, nf = cycle
    reserved = open_ne(application, gestor, ata["id"], [(items[1]["id"], "100")])
    to_stage(application, gestor, reserved.json()["id"], "pre_empenho")
    draft = open_ne(application, gestor, ata["id"], [(items[1]["id"], "50")])
    assert draft.status_code == 201, draft.text
    reference = instant()
    before = {
        name: read(application, gestor, name, referencia=reference, ata_id=ata["id"])[1]
        for name in NAMES
    }

    aditivo = application.post(
        f"{ATAS}/{ata['id']}/aditivos",
        json={"kind": "valor", "valor_acrescimo": "5000.00", "justification": "Aditivo."},
        headers=gestor,
    )
    assert aditivo.status_code == 201, aditivo.text
    to_stage(application, gestor, reserved.json()["id"], "ne_emitida")
    replaced = application.put(
        f"{NES}/{draft.json()['id']}/itens",
        json={"items": [{"item_ata_id": items[1]["id"], "quantity": "80"}]},
        headers=gestor,
    )
    assert replaced.status_code == 200, replaced.text
    later = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")])
    assert later.status_code == 201, later.text
    moved(application, gestor, nf["id"], "enviar")

    after = {
        name: read(application, gestor, name, referencia=reference, ata_id=ata["id"])[1]
        for name in NAMES
    }
    assert after == before
    (position,) = before["posicao-saldo"]
    assert position["Valor contratado"] == "100000,00"
    assert position["Valor reservado"] == "200,00"
    assert position["Valor empenhado"] == "3000,00"
    assert position["Saldo disponível"] == "96800,00"
    assert position["Comprometimento (%)"] == "3,20"
    assert position["Alto consumo"] == "Não"
    assert sorted((row["Etapa"], row["Valor"]) for row in before["execucao-orcamentaria"]) == [
        ("Demanda", "100,00"),
        ("NE emitida", "3000,00"),
        ("Pré-empenho", "200,00"),
    ]
    assert before["notas-fiscais-em-conferencia"] == []
    (fornecedor,) = before["indicadores-fornecedores"]
    assert fornecedor["Valor empenhado"] == "3000,00"
    assert (fornecedor["NFs lançadas"], fornecedor["NFs aprovadas"]) == ("1", "0")


def test_AC_0009_03_a_report_without_a_reference_reads_the_present(
    application: TestClient,
    gestor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """With no data de referência the figures are those of the instant of the request."""
    ata, items, _, nf = cycle
    reference = instant()
    reserved = open_ne(application, gestor, ata["id"], [(items[1]["id"], "100")])
    to_stage(application, gestor, reserved.json()["id"], "pre_empenho")
    moved(application, gestor, nf["id"], "enviar")

    (now,) = read(application, gestor, "posicao-saldo", ata_id=ata["id"])[1]
    (then,) = read(application, gestor, "posicao-saldo", referencia=reference, ata_id=ata["id"])[1]
    (waiting,) = read(application, gestor, "notas-fiscais-em-conferencia", ata_id=ata["id"])[1]

    assert (then["Valor reservado"], now["Valor reservado"]) == ("0,00", "200,00")
    assert waiting["Valor"] == "1000,00"
    assert waiting["ATA"] == ata["number"]


def test_AC_0009_03_what_did_not_exist_at_the_reference_stays_out(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """An ATA created after the reference has no row in a report at that reference."""
    reference = instant()
    ata, _ = setup_ata(application, gestor, [("10", "1")])

    assert (
        read(application, gestor, "posicao-saldo", referencia=reference, ata_id=ata["id"])[1] == []
    )
    assert len(read(application, gestor, "posicao-saldo", ata_id=ata["id"])[1]) == 1


def test_AC_0009_03_the_first_change_after_the_reference_holds_the_prior_value() -> None:
    """Of two changes to a field, the older one says what it held at the reference."""
    entity, other = uuid.uuid4(), uuid.uuid4()
    rows = [
        AuditLog(entidade_id=entity, dados_anteriores={"status": "pre_empenho"}),
        AuditLog(
            entidade_id=entity, dados_anteriores={"status": "envio_fornecedor", "numero": "7"}
        ),
        AuditLog(entidade_id=other, dados_anteriores={"item_ata_id": "x", "status": "removido"}),
        AuditLog(entidade_id=other, dados_anteriores=None),
    ]

    assert rewound(rows) == {entity: {"status": "pre_empenho", "numero": "7"}, other: {}}


# ── AC-0009-04 ─ the export is audited ───────────────────────────────────────


def test_AC_0009_04_an_export_writes_who_took_which_report(
    application: TestClient,
    gestor_user: tuple[dict, User],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """The history holds one row per export, under the identifier the file prints."""
    headers, user = gestor_user
    ata = cycle[0]

    header, _ = read(application, headers, "posicao-saldo", ata_id=ata["id"])

    page = application.get(
        HIST, params={"entidade_tipo": "relatorio", "usuario_id": str(user.id)}, headers=headers
    )
    assert page.status_code == 200, page.text
    (row,) = page.json()["items"]
    assert row["acao"] == "relatorio.exportado"
    assert row["entidade_id"] == header["Identificador"]
    assert row["dados_anteriores"]["relatorio"] == "posicao-saldo"
    assert row["dados_anteriores"]["formato"] == "csv"
    assert row["dados_anteriores"]["ata_id"] == ata["id"]
    assert row["dados_anteriores"]["colunas"] is None
    assert row["dados_anteriores"]["inicio"] is None


def test_AC_0009_04_an_export_writes_its_columns_and_its_window(
    application: TestClient,
    gestor_user: tuple[dict, User],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """The history row says which columns left and from which instant."""
    headers, user = gestor_user
    start = instant()

    read(
        application,
        headers,
        "execucao-orcamentaria",
        ata_id=cycle[0]["id"],
        colunas="value,ne",
        inicio=start,
    )

    page = application.get(
        HIST, params={"entidade_tipo": "relatorio", "usuario_id": str(user.id)}, headers=headers
    )
    assert page.status_code == 200, page.text
    (row,) = page.json()["items"]
    assert row["dados_anteriores"]["colunas"] == ["ne", "value"]
    assert datetime.datetime.fromisoformat(
        row["dados_anteriores"]["inicio"]
    ) == datetime.datetime.fromisoformat(start)


# ── AC-0009-05 ─ who may export ──────────────────────────────────────────────


@pytest.mark.parametrize("relatorio", NAMES)
def test_AC_0009_05_an_auditor_generates_every_report(
    application: TestClient, auditor: dict[str, str], relatorio: str
) -> None:
    """The auditor is served each of the four."""
    assert application.get(f"{REPORTS}/{relatorio}", headers=auditor).status_code == 200


def test_AC_0009_05_a_servidor_is_refused(
    application: TestClient, servidor: dict[str, str]
) -> None:
    """A servidor gets 403, not a partial report."""
    response = application.get(f"{REPORTS}/posicao-saldo", headers=servidor)

    assert response.status_code == 403
    assert error(response)["code"] == "PERFIL_NAO_AUTORIZADO"


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_AC_0009_05_no_report_route_accepts_a_write(
    application: TestClient, gestor: dict[str, str], method: str
) -> None:
    """Every write method on a report answers 405."""
    response = application.request(method, f"{REPORTS}/posicao-saldo", headers=gestor)

    assert response.status_code == 405


# ── AC-0009-06 ─ the CSV Excel opens ─────────────────────────────────────────


def test_AC_0009_06_the_csv_opens_in_excel_pt_br(
    application: TestClient,
    gestor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """UTF-8 with BOM, `;` between cells, CRLF between rows and the comma in figures."""
    response = application.get(
        f"{REPORTS}/posicao-saldo", params={"ata_id": cycle[0]["id"]}, headers=gestor
    )

    assert response.headers["content-type"].startswith("text/csv")
    assert response.content.startswith(BOM)
    text = response.content.decode("utf-8-sig")
    assert "ATA;Fornecedor;Situação;Fim da vigência;Valor contratado" in text
    assert ";100000,00;" in text
    assert text.endswith("\r\n") and "\n" not in text.replace("\r\n", "")


@pytest.mark.parametrize(
    ("cell", "written"),
    [
        ("=SOMA(A1:A9)", "'=SOMA(A1:A9)"),
        ("+55 48", "'+55 48"),
        ("@fornecedor", "'@fornecedor"),
        ("-Fornecedor", "'-Fornecedor"),
        ("-700,00", "-700,00"),
        ("Fornecedor Ltda", "Fornecedor Ltda"),
    ],
)
def test_AC_0009_06_a_text_cell_cannot_start_a_formula(cell: str, written: str) -> None:
    """A cell a spreadsheet would run is neutralised; a negative figure is left alone."""
    assert relatorio_files.safe(cell) == written


# ── AC-0009-08 ─ the caller chooses the columns ──────────────────────────────


def test_AC_0009_08_the_chosen_columns_keep_the_order_of_the_report() -> None:
    """The choice says which columns, never in which order, and a repeat counts once."""
    assert chosen("posicao-saldo", None) == tuple(range(10))
    assert chosen("posicao-saldo", ("saldo_disponivel", "ata", "ata")) == (0, 7)


@pytest.mark.parametrize("colunas", [(), ("xyz",), ("ata", "xyz")])
def test_AC_0009_08_an_unknown_or_empty_choice_is_refused(colunas: tuple[str, ...]) -> None:
    """No column, or one the report does not have, is an error on `colunas`."""
    with pytest.raises(InvalidData) as raised:
        chosen("posicao-saldo", colunas)

    assert "colunas" in raised.value.fields


def test_AC_0009_08_an_export_carries_only_the_chosen_columns(
    application: TestClient, gestor: dict[str, str], cycle: tuple[dict, list[dict], dict, dict]
) -> None:
    """A file asked for two columns has those two and no other."""
    _, rows = read(
        application, gestor, "posicao-saldo", ata_id=cycle[0]["id"], colunas="saldo_disponivel, ata"
    )

    (row,) = rows
    assert list(row) == ["ATA", "Saldo disponível"]
    assert row["ATA"] == cycle[0]["number"]


@pytest.mark.parametrize("colunas", ["xyz", ","])
def test_AC_0009_08_a_wrong_choice_answers_422(
    application: TestClient, gestor: dict[str, str], colunas: str
) -> None:
    """An unknown column and an empty list answer 422 on `colunas`."""
    response = application.get(
        f"{REPORTS}/posicao-saldo", params={"colunas": colunas}, headers=gestor
    )

    assert response.status_code == 422, response.text
    assert error(response)["code"] == "INVALID_DATA"
    assert "colunas" in error(response)["fields"]


# ── AC-0009-09 ─ the caller chooses the time window ──────────────────────────


@pytest.mark.parametrize("relatorio", ["execucao-orcamentaria", "notas-fiscais-em-conferencia"])
def test_AC_0009_09_what_was_registered_before_the_window_stays_out(
    application: TestClient,
    gestor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
    relatorio: str,
) -> None:
    """An NE and an NF registered before `inicio` have no row; without it they do."""
    ata = cycle[0]
    start = instant()

    header, rows = read(application, gestor, relatorio, ata_id=ata["id"], inicio=start)

    assert rows == []
    assert header["Período"].startswith("De ") and " até " in header["Período"]
    assert len(read(application, gestor, relatorio, ata_id=ata["id"])[1]) == 1


def test_AC_0009_09_what_was_registered_inside_the_window_is_listed(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """An NE registered after `inicio` is in the window."""
    start = instant()
    ata, items = setup_ata(application, gestor, [("1000", "10")])
    created = open_ne(application, gestor, ata["id"], [(items[0]["id"], "300")])
    assert created.status_code == 201, created.text

    _, rows = read(application, gestor, "execucao-orcamentaria", ata_id=ata["id"], inicio=start)

    assert len(rows) == 1


def test_AC_0009_09_the_posicao_de_saldo_has_no_window(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """Saldo is a position at an instant, so `inicio` is refused there."""
    response = application.get(
        f"{REPORTS}/posicao-saldo", params={"inicio": instant()}, headers=gestor
    )

    assert response.status_code == 422, response.text
    assert "inicio" in error(response)["fields"]


def test_AC_0009_09_a_window_cannot_start_after_its_reference(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """`inicio` later than `referencia` answers 422 on `inicio`."""
    reference = instant()
    response = application.get(
        f"{REPORTS}/execucao-orcamentaria",
        params={"referencia": reference, "inicio": instant()},
        headers=gestor,
    )

    assert response.status_code == 422, response.text
    assert "inicio" in error(response)["fields"]
