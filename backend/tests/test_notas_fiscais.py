"""The NF conference — SPEC-0005 v1.1.

An NF is launched against an issued NE and never against an ATA (RN02). Both caps,
value and quantity, are asserted at registration, correction and resend, and the
ATA's saldo is shown untouched by every launch (AC-0005-10, ADR-0015).
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Callable

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import clock
from app.models.user import User
from tests.catalogue import CNPJ, audit_rows, login, new_cnpj
from tests.test_notas_empenho import item_saldo, numero, open_ne, saldo, setup_ata, to_stage

NFS = "/api/v1/notas-fiscais"
NES = "/api/v1/notas-empenho"
ACTIONS = ("enviar", "aprovar", "devolver", "quarentena", "liberar")


def today() -> datetime.date:
    """Today in São Paulo, the day an NE issued now carries."""
    return clock.local_date(clock.now())


def d(value: object) -> decimal.Decimal:
    """A decimal from the string the API answers with."""
    return decimal.Decimal(str(value))


@pytest.fixture
def gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in gestor."""
    return login(application, create_user, "gestor")[0]


@pytest.fixture
def servidor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in servidor."""
    return login(application, create_user, "servidor")[0]


@pytest.fixture
def auditor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in auditor."""
    return login(application, create_user, "auditor")[0]


@pytest.fixture
def issued(application: TestClient, gestor: dict[str, str]) -> tuple[dict, list[dict], dict]:
    """An ATA of 1000 units at R$ 10,00 and an issued NE of 300 of them (R$ 3.000,00)."""
    ata, items = setup_ata(application, gestor, [("1000", "10")])
    created = open_ne(application, gestor, ata["id"], [(items[0]["id"], "300")])
    assert created.status_code == 201, created.text
    ne = to_stage(application, gestor, created.json()["id"], "ne_emitida")
    return ata, items, ne


def line_of(ne: dict) -> str:
    """The id of the NE's only line."""
    return str(ne["items"][0]["id"])


def nf_body(ne: dict, quantidade: str, valor: str, **override: object) -> dict[str, object]:
    """An NF against the NE's only line, dated today, from the ATA's fornecedor."""
    body: dict[str, object] = {
        "nota_empenho_id": ne["id"],
        "numero": numero(),
        "data_emissao": today().isoformat(),
        "valor": valor,
        "fornecedor_cnpj": CNPJ,
        "itens": [{"item_nota_empenho_id": line_of(ne), "quantidade": quantidade}],
    }
    body.update(override)
    return body


def register(
    application: TestClient, headers: dict[str, str], body: dict[str, object]
) -> httpx2.Response:
    """POST an NF; the raw response."""
    return application.post(NFS, json=body, headers=headers)


def launched(
    application: TestClient, headers: dict[str, str], ne: dict, quantidade: str, valor: str
) -> dict:
    """An NF registered against the NE; it must succeed."""
    response = register(application, headers, nf_body(ne, quantidade, valor))
    assert response.status_code == 201, response.text
    return response.json()


def act(
    application: TestClient, headers: dict[str, str], nf_id: str, action: str, **body: object
) -> httpx2.Response:
    """One conference action on an NF."""
    return application.post(f"{NFS}/{nf_id}/{action}", json=body, headers=headers)


def moved(
    application: TestClient, headers: dict[str, str], nf_id: str, action: str, **body: object
) -> dict:
    """One conference action that must succeed; the NF as it ends."""
    response = act(application, headers, nf_id, action, **body)
    assert response.status_code == 200, response.text
    return response.json()


def ne_line(application: TestClient, headers: dict[str, str], ne_id: str) -> dict:
    """The NE's only line, with recebida, em quarentena and faltante."""
    response = application.get(f"{NES}/{ne_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["items"][0]


def nf_count(db_session: Session) -> int:
    """How many NFs exist."""
    db_session.rollback()
    return int(db_session.execute(text("SELECT count(*) FROM nota_fiscal")).scalar_one())


def error(response: httpx2.Response) -> dict:
    """The error envelope of a refused request."""
    return response.json()["error"]


# ── AC-0005-01 ─ the required fields ─────────────────────────────────────────


@pytest.mark.parametrize(
    "field", ["numero", "data_emissao", "valor", "fornecedor_cnpj", "nota_empenho_id"]
)
def test_AC_0005_01_each_missing_field_is_named(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session, field: str
) -> None:
    """A registration without one of the fields is refused, naming it."""
    _, _, ne = issued
    before = nf_count(db_session)
    body = nf_body(ne, "100", "1000.00")
    del body[field]
    response = register(application, gestor, body)
    assert response.status_code == 422
    assert field in error(response)["fields"]
    assert nf_count(db_session) == before


def test_AC_0005_01_blank_numero_empty_itens_and_bad_cnpj(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """A blank número, no lines or an invalid CNPJ are refused on their own field."""
    _, _, ne = issued
    before = nf_count(db_session)

    blank = register(application, gestor, nf_body(ne, "100", "1000.00", numero="   "))
    assert blank.status_code == 422
    assert error(blank)["fields"] == {"numero": "Informe o número."}

    empty = register(application, gestor, nf_body(ne, "100", "1000.00", itens=[]))
    assert empty.status_code == 422
    assert error(empty)["fields"] == {"itens": "Informe ao menos um item."}

    bad = register(
        application, gestor, nf_body(ne, "100", "1000.00", fornecedor_cnpj="11.222.333/0001-00")
    )
    assert bad.status_code == 422
    assert error(bad)["fields"] == {"fornecedor_cnpj": "Informe um CNPJ válido."}

    assert nf_count(db_session) == before


# ── AC-0005-02 ─ an NF binds to an NE, never to an ATA (RN02) ────────────────


def test_AC_0005_02_RN02_the_ata_comes_through_the_ne(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """The NF carries the NE it was launched against and inherits the NE's ATA."""
    ata, _, ne = issued
    other, _ = setup_ata(application, gestor, [("10", "1")])
    body = nf_body(ne, "100", "1000.00", ata_id=other["id"])
    response = register(application, gestor, body)
    assert response.status_code == 201, response.text
    nf = response.json()
    assert nf["nota_empenho_id"] == ne["id"]
    assert nf["nota_empenho_number"] == ne["number"]
    assert nf["ata_id"] == ata["id"]
    assert nf["status"] == "aguardando"
    assert nf["quarentena"] is False


# ── AC-0005-03 ─ only an issued NE receives NFs ──────────────────────────────


@pytest.mark.parametrize(
    ("stage", "label"),
    [
        ("demanda", "Demanda"),
        ("validacao_saldo", "Validação de saldo"),
        ("pre_empenho", "Pré-empenho"),
        ("envio_fornecedor", "Envio ao fornecedor"),
        ("cancelada", "Cancelada"),
    ],
)
def test_AC_0005_03_an_ne_not_issued_refuses_the_nf(
    application: TestClient,
    gestor: dict[str, str],
    db_session: Session,
    stage: str,
    label: str,
) -> None:
    """An NE in any stage but ne_emitida refuses an NF, naming its stage."""
    ata, items = setup_ata(application, gestor, [("1000", "10")])
    created = open_ne(application, gestor, ata["id"], [(items[0]["id"], "300")])
    assert created.status_code == 201, created.text
    ne = to_stage(application, gestor, created.json()["id"], stage)
    before = nf_count(db_session)
    response = register(application, gestor, nf_body(ne, "100", "1000.00"))
    assert response.status_code == 409
    assert error(response)["code"] == "NE_NAO_EMITIDA"
    assert label in error(response)["message"]
    assert nf_count(db_session) == before


def test_AC_0005_03_an_unknown_ne_is_not_found(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """An NF against an NE that does not exist is a 404."""
    _, _, ne = issued
    response = register(
        application, gestor, nf_body(ne, "100", "1000.00", nota_empenho_id=str(uuid.uuid4()))
    )
    assert response.status_code == 404


# ── AC-0005-04 ─ no future date ──────────────────────────────────────────────


def test_AC_0005_04_a_future_emission_date_is_refused(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """An NF dated tomorrow is refused on data_emissao."""
    _, _, ne = issued
    before = nf_count(db_session)
    tomorrow = (today() + datetime.timedelta(days=1)).isoformat()
    response = register(application, gestor, nf_body(ne, "100", "1000.00", data_emissao=tomorrow))
    assert response.status_code == 422
    assert error(response)["fields"] == {"data_emissao": "A data de emissão não pode ser futura."}
    assert nf_count(db_session) == before


# ── AC-0005-05 ─ an NF older than its NE needs confirming ────────────────────


def test_AC_0005_05_a_back_dated_nf_needs_confirmation(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """Dated before the NE, the NF is held until confirmed, and the confirmation is audited."""
    _, _, ne = issued
    yesterday = (today() - datetime.timedelta(days=1)).isoformat()
    before = nf_count(db_session)

    held = register(application, gestor, nf_body(ne, "100", "1000.00", data_emissao=yesterday))
    assert held.status_code == 409
    assert error(held)["code"] == "DATA_ANTERIOR_AO_EMPENHO"
    assert nf_count(db_session) == before

    confirmed = register(
        application,
        gestor,
        nf_body(ne, "100", "1000.00", data_emissao=yesterday, confirmar_data_anterior=True),
    )
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["data_emissao"] == yesterday
    rows = audit_rows(db_session, confirmed.json()["id"], "nf.registrada")
    assert len(rows) == 1
    assert rows[0].dados_anteriores == {"confirmar_data_anterior": True}

    plain = launched(application, gestor, ne, "100", "1000.00")
    assert audit_rows(db_session, plain["id"], "nf.registrada")[0].dados_anteriores is None


# ── AC-0005-06 ─ the fornecedor is the ATA's ─────────────────────────────────


def test_AC_0005_06_another_fornecedor_is_refused(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """A CNPJ that is not the ATA's fornecedor is refused; the unmasked one is the same."""
    ata, _, ne = issued
    before = nf_count(db_session)
    other = register(application, gestor, nf_body(ne, "100", "1000.00", fornecedor_cnpj=new_cnpj()))
    assert other.status_code == 409
    assert error(other)["code"] == "FORNECEDOR_DIVERGENTE"
    assert nf_count(db_session) == before

    unmasked = register(
        application, gestor, nf_body(ne, "100", "1000.00", fornecedor_cnpj="11222333000181")
    )
    assert unmasked.status_code == 201, unmasked.text
    assert unmasked.json()["fornecedor_id"] == ata["fornecedor"]["id"]


# ── AC-0005-07 ─ RN12, the NFs never bill past the NE ────────────────────────


def test_AC_0005_07_RN12_the_value_cap(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """Past the NE's value the NF is refused; a devolvida NF stops counting."""
    _, _, ne = issued
    first = launched(application, gestor, ne, "100", "2000.00")
    before = nf_count(db_session)

    over = register(application, gestor, nf_body(ne, "100", "1500.00"))
    assert over.status_code == 409
    assert error(over)["code"] == "VALOR_ACIMA_DO_EMPENHO"
    assert "R$ 3.500,00" in error(over)["message"]
    assert "R$ 3.000,00" in error(over)["message"]
    assert nf_count(db_session) == before

    moved(application, gestor, first["id"], "enviar")
    moved(application, gestor, first["id"], "devolver", justificativa="Valor divergente.")
    launched(application, gestor, ne, "100", "1500.00")


def test_AC_0005_07_RN12_a_quarantined_nf_still_counts(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """Quarantine holds the NF but does not free its value."""
    _, _, ne = issued
    held = launched(application, gestor, ne, "250", "2500.00")
    moved(application, gestor, held["id"], "quarentena", motivo="Caixa avariada.")
    over = register(application, gestor, nf_body(ne, "60", "600.00"))
    assert over.status_code == 409
    assert error(over)["code"] == "VALOR_ACIMA_DO_EMPENHO"


# ── AC-0005-08 ─ the conference ──────────────────────────────────────────────


def test_AC_0005_08_the_conference_walks_its_statuses(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """The walk aguardando, em_conferencia, devolvida, em_conferencia, aprovada, then nothing."""
    _, _, ne = issued
    nf = launched(application, gestor, ne, "100", "1000.00")

    for action, body in (("aprovar", {}), ("devolver", {"justificativa": "Erro."})):
        early = act(application, gestor, nf["id"], action, **body)
        assert early.status_code == 409
        assert error(early)["code"] == "TRANSICAO_INVALIDA"

    assert moved(application, gestor, nf["id"], "enviar")["status"] == "em_conferencia"
    again = act(application, gestor, nf["id"], "enviar")
    assert again.status_code == 409
    assert error(again)["code"] == "TRANSICAO_INVALIDA"

    assert act(application, gestor, nf["id"], "devolver").status_code == 422
    assert act(application, gestor, nf["id"], "devolver", justificativa="  ").status_code == 422
    returned = moved(
        application, gestor, nf["id"], "devolver", justificativa="Quantidade divergente."
    )
    assert returned["status"] == "devolvida"
    assert returned["justificativa_devolucao"] == "Quantidade divergente."
    row = audit_rows(db_session, nf["id"], "nf.devolvida")[0]
    assert row.justificativa == "Quantidade divergente."
    assert row.dados_anteriores["status"] == "em_conferencia"

    assert moved(application, gestor, nf["id"], "enviar")["status"] == "em_conferencia"
    assert moved(application, gestor, nf["id"], "aprovar")["status"] == "aprovada"
    assert len(audit_rows(db_session, nf["id"], "nf.enviada")) == 2
    assert len(audit_rows(db_session, nf["id"], "nf.aprovada")) == 1

    for action, body in (
        ("enviar", {}),
        ("aprovar", {}),
        ("devolver", {"justificativa": "Erro."}),
        ("quarentena", {"motivo": "Erro."}),
        ("liberar", {}),
    ):
        late = act(application, gestor, nf["id"], action, **body)
        assert late.status_code == 409, action
        assert error(late)["code"] == "TRANSICAO_INVALIDA"


def test_AC_0005_08_resending_a_devolvida_nf_reruns_the_caps(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """A devolvida NF whose room another NF took cannot come back."""
    _, _, ne = issued
    first = launched(application, gestor, ne, "100", "2000.00")
    moved(application, gestor, first["id"], "enviar")
    moved(application, gestor, first["id"], "devolver", justificativa="Valor divergente.")
    launched(application, gestor, ne, "100", "2000.00")

    resend = act(application, gestor, first["id"], "enviar")
    assert resend.status_code == 409
    assert error(resend)["code"] == "VALOR_ACIMA_DO_EMPENHO"
    current = application.get(f"{NFS}/{first['id']}", headers=gestor).json()
    assert current["status"] == "devolvida"


def test_AC_0005_08_an_unknown_nf_is_not_found(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """An action on an NF that does not exist is a 404."""
    response = act(application, gestor, str(uuid.uuid4()), "enviar")
    assert response.status_code == 404
    assert error(response)["code"] == "NOT_FOUND"


# ── AC-0005-09 ─ who moves the conference ────────────────────────────────────


def test_AC_0005_09_the_servidor_launches_but_does_not_decide(
    application: TestClient,
    gestor: dict[str, str],
    servidor: dict[str, str],
    issued: tuple,
) -> None:
    """A servidor registers, sends and quarantines; the decisions are the gestor's."""
    _, _, ne = issued
    nf = launched(application, servidor, ne, "100", "1000.00")
    moved(application, servidor, nf["id"], "enviar")

    for action, body in (("aprovar", {}), ("devolver", {"justificativa": "Erro."})):
        refused = act(application, servidor, nf["id"], action, **body)
        assert refused.status_code == 403, action
        assert error(refused)["code"] == "PERFIL_NAO_AUTORIZADO"

    moved(application, servidor, nf["id"], "quarentena", motivo="Lote vencido.")
    refused = act(application, servidor, nf["id"], "liberar")
    assert refused.status_code == 403
    assert error(refused)["code"] == "PERFIL_NAO_AUTORIZADO"
    moved(application, gestor, nf["id"], "liberar")
    assert moved(application, gestor, nf["id"], "aprovar")["status"] == "aprovada"


def test_AC_0005_09_the_auditor_only_reads(
    application: TestClient, gestor: dict[str, str], auditor: dict[str, str], issued: tuple
) -> None:
    """An auditor is refused every write and reads the list and the NF."""
    _, _, ne = issued
    nf = launched(application, gestor, ne, "100", "1000.00")

    writes = [
        application.post(NFS, json=nf_body(ne, "10", "100.00"), headers=auditor),
        application.put(f"{NFS}/{nf['id']}", json=nf_body(ne, "10", "100.00"), headers=auditor),
        act(application, auditor, nf["id"], "enviar"),
        act(application, auditor, nf["id"], "aprovar"),
        act(application, auditor, nf["id"], "devolver", justificativa="Erro."),
        act(application, auditor, nf["id"], "quarentena", motivo="Erro."),
        act(application, auditor, nf["id"], "liberar"),
    ]
    for response in writes:
        assert response.status_code == 403, response.request.url
        assert error(response)["code"] == "PERFIL_NAO_AUTORIZADO"

    assert application.get(NFS, headers=auditor).status_code == 200
    assert application.get(f"{NFS}/{nf['id']}", headers=auditor).status_code == 200


# ── AC-0005-10 ─ a launch never touches saldo (ADR-0015) ─────────────────────


def test_AC_0005_10_the_saldo_is_untouched_by_the_conference(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """Registering, sending and approving an NF leave the ATA's saldo as it was."""
    ata, items, ne = issued

    def snapshot() -> tuple[dict, dict]:
        value = saldo(application, gestor, ata["id"])
        value.pop("calculado_em")
        return value, item_saldo(application, gestor, ata["id"], items[0]["id"])

    before = snapshot()
    nf = launched(application, gestor, ne, "100", "1000.00")
    assert snapshot() == before
    moved(application, gestor, nf["id"], "enviar")
    assert snapshot() == before
    moved(application, gestor, nf["id"], "aprovar")
    assert snapshot() == before
    assert d(ne_line(application, gestor, ne["id"])["quantidade_faltante"]) == 200


# ── AC-0005-12 ─ the quantity of each line ───────────────────────────────────


def test_AC_0005_12_the_ne_line_shows_what_came(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """100 of 300 delivered: recebida 100, faltante 200."""
    _, _, ne = issued
    launched(application, gestor, ne, "100", "1000.00")
    line = ne_line(application, gestor, ne["id"])
    assert d(line["quantidade_recebida"]) == 100
    assert d(line["quantidade_em_quarentena"]) == 0
    assert d(line["quantidade_faltante"]) == 200


def test_AC_0005_12_each_line_belongs_to_the_ne_once(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """A line of another NE, a zero quantity and a repeated line are refused on the line."""
    ata, items, ne = issued
    other = open_ne(application, gestor, ata["id"], [(items[0]["id"], "10")]).json()
    before = nf_count(db_session)

    foreign = register(
        application,
        gestor,
        nf_body(
            ne,
            "10",
            "100.00",
            itens=[{"item_nota_empenho_id": other["items"][0]["id"], "quantidade": "10"}],
        ),
    )
    assert foreign.status_code == 422
    assert error(foreign)["fields"] == {
        "itens.0.item_nota_empenho_id": "Item da NE não encontrado."
    }

    zero = register(application, gestor, nf_body(ne, "0", "100.00"))
    assert zero.status_code == 422
    assert "itens.0.quantidade" in error(zero)["fields"]

    line = {"item_nota_empenho_id": line_of(ne), "quantidade": "10"}
    repeated = register(application, gestor, nf_body(ne, "10", "200.00", itens=[line, line]))
    assert repeated.status_code == 422
    assert error(repeated)["code"] == "ITEM_DUPLICADO"
    assert "itens.1.item_nota_empenho_id" in error(repeated)["fields"]

    assert nf_count(db_session) == before


def test_AC_0005_12_the_quantity_cap(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """Within the value, a delivery past the NE's quantity is still refused."""
    _, _, ne = issued
    launched(application, gestor, ne, "250", "2500.00")
    before = nf_count(db_session)
    over = register(application, gestor, nf_body(ne, "100", "400.00"))
    assert over.status_code == 409
    assert error(over)["code"] == "QUANTIDADE_ACIMA_DO_EMPENHO"
    assert nf_count(db_session) == before


# ── AC-0005-13 ─ quarantine ──────────────────────────────────────────────────


def test_AC_0005_13_quarantine_holds_and_release_frees(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """A held NF counts apart, cannot be approved, and is released by the gestor."""
    _, _, ne = issued
    nf = launched(application, gestor, ne, "100", "1000.00")

    assert act(application, gestor, nf["id"], "quarentena").status_code == 422
    not_held = act(application, gestor, nf["id"], "liberar")
    assert not_held.status_code == 409
    assert error(not_held)["code"] == "TRANSICAO_INVALIDA"

    held = moved(application, gestor, nf["id"], "quarentena", motivo="Caixa avariada.")
    assert held["quarentena"] is True
    assert held["motivo_quarentena"] == "Caixa avariada."
    line = ne_line(application, gestor, ne["id"])
    assert d(line["quantidade_em_quarentena"]) == 100
    assert d(line["quantidade_recebida"]) == 0
    assert d(line["quantidade_faltante"]) == 300

    twice = act(application, gestor, nf["id"], "quarentena", motivo="De novo.")
    assert twice.status_code == 409
    assert error(twice)["code"] == "TRANSICAO_INVALIDA"

    assert moved(application, gestor, nf["id"], "enviar")["status"] == "em_conferencia"
    blocked = act(application, gestor, nf["id"], "aprovar")
    assert blocked.status_code == 409
    assert error(blocked)["code"] == "NF_EM_QUARENTENA"

    released = moved(application, gestor, nf["id"], "liberar")
    assert released["quarentena"] is False
    assert d(ne_line(application, gestor, ne["id"])["quantidade_recebida"]) == 100
    assert moved(application, gestor, nf["id"], "aprovar")["status"] == "aprovada"

    started = audit_rows(db_session, nf["id"], "nf.quarentena_iniciada")
    ended = audit_rows(db_session, nf["id"], "nf.quarentena_liberada")
    assert len(started) == 1
    assert started[0].dados_anteriores["motivo"] == "Caixa avariada."
    assert len(ended) == 1
    assert ended[0].dados_anteriores["motivo"] == "Caixa avariada."


# ── AC-0005-14 ─ correcting before the conference ────────────────────────────


def test_AC_0005_14_an_aguardando_nf_is_corrected(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """The header and lines are replaced and the old values audited."""
    _, _, ne = issued
    nf = launched(application, gestor, ne, "300", "3000.00")
    body = nf_body(ne, "290", "2900.00")
    del body["nota_empenho_id"]
    response = application.put(f"{NFS}/{nf['id']}", json=body, headers=gestor)
    assert response.status_code == 200, response.text
    corrected = response.json()
    assert corrected["numero"] == body["numero"]
    assert d(corrected["valor"]) == decimal.Decimal("2900.00")
    assert d(corrected["itens"][0]["quantidade"]) == 290
    assert corrected["nota_empenho_id"] == ne["id"]

    row = audit_rows(db_session, nf["id"], "nf.corrigida")[0]
    assert row.dados_anteriores["numero"] == nf["numero"]
    assert d(row.dados_anteriores["valor"]) == decimal.Decimal("3000.00")
    assert d(row.dados_anteriores["itens"][0]["quantidade"]) == 300


def test_AC_0005_14_only_before_the_conference(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """A devolvida NF is corrected; one in conference or approved is not."""
    _, _, ne = issued
    nf = launched(application, gestor, ne, "100", "1000.00")
    body = nf_body(ne, "90", "900.00")
    del body["nota_empenho_id"]

    moved(application, gestor, nf["id"], "enviar")
    in_conference = application.put(f"{NFS}/{nf['id']}", json=body, headers=gestor)
    assert in_conference.status_code == 409
    assert error(in_conference)["code"] == "NF_NAO_EDITAVEL"

    moved(application, gestor, nf["id"], "devolver", justificativa="Valor divergente.")
    fixed = application.put(f"{NFS}/{nf['id']}", json=body, headers=gestor)
    assert fixed.status_code == 200, fixed.text

    moved(application, gestor, nf["id"], "enviar")
    moved(application, gestor, nf["id"], "aprovar")
    approved = application.put(f"{NFS}/{nf['id']}", json=body, headers=gestor)
    assert approved.status_code == 409
    assert error(approved)["code"] == "NF_NAO_EDITAVEL"


# ── AC-0005-15 ─ one número per fornecedor ───────────────────────────────────


def test_AC_0005_15_the_numero_is_unique_per_fornecedor(
    application: TestClient, gestor: dict[str, str], issued: tuple, db_session: Session
) -> None:
    """The same número of the same fornecedor is refused, even on another NE."""
    ata, items, ne = issued
    nf = launched(application, gestor, ne, "100", "1000.00")
    second = open_ne(application, gestor, ata["id"], [(items[0]["id"], "100")]).json()
    second = to_stage(application, gestor, second["id"], "ne_emitida")
    before = nf_count(db_session)

    duplicate = register(application, gestor, nf_body(second, "10", "100.00", numero=nf["numero"]))
    assert duplicate.status_code == 409
    assert error(duplicate)["code"] == "NF_DUPLICADA"
    assert nf_count(db_session) == before


def test_AC_0005_15_another_fornecedor_may_reuse_the_numero(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """The same número from a different fornecedor is a different NF."""
    _, _, ne = issued
    nf = launched(application, gestor, ne, "100", "1000.00")
    cnpj = new_cnpj()
    ata, items = setup_ata(
        application, gestor, [("100", "10")], fornecedor={"cnpj": cnpj, "legal_name": "Outra Ltda"}
    )
    created = open_ne(application, gestor, ata["id"], [(items[0]["id"], "50")]).json()
    other = to_stage(application, gestor, created["id"], "ne_emitida")
    response = register(
        application,
        gestor,
        nf_body(other, "10", "100.00", numero=nf["numero"], fornecedor_cnpj=cnpj),
    )
    assert response.status_code == 201, response.text


# ── AC-0005-16 ─ the list and the detail ─────────────────────────────────────


def test_AC_0005_16_list_filters_and_detail(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """The NFs of an NE, newest first, by status and quarantine; the detail names the insumo."""
    _, items, ne = issued
    first = launched(application, gestor, ne, "100", "1000.00")
    second = launched(application, gestor, ne, "50", "500.00")
    moved(application, gestor, second["id"], "enviar")
    moved(application, gestor, first["id"], "quarentena", motivo="Caixa avariada.")

    page = application.get(NFS, params={"nota_empenho_id": ne["id"]}, headers=gestor).json()
    assert page["total"] == 2
    assert [n["id"] for n in page["items"]] == [second["id"], first["id"]]

    sent = application.get(
        NFS, params={"nota_empenho_id": ne["id"], "status": "em_conferencia"}, headers=gestor
    ).json()
    assert [n["id"] for n in sent["items"]] == [second["id"]]

    held = application.get(
        NFS, params={"nota_empenho_id": ne["id"], "quarentena": "true"}, headers=gestor
    ).json()
    assert [n["id"] for n in held["items"]] == [first["id"]]

    detail = application.get(f"{NFS}/{first['id']}", headers=gestor)
    assert detail.status_code == 200
    line = detail.json()["itens"][0]
    assert line["item_nota_empenho_id"] == line_of(ne)
    assert line["item_ata_id"] == items[0]["id"]
    assert line["insumo_id"] == items[0]["insumo"]["id"]
    assert line["sku"]
    assert line["description"]
    assert line["unit"]

    missing = application.get(f"{NFS}/{uuid.uuid4()}", headers=gestor)
    assert missing.status_code == 404
    assert error(missing)["code"] == "NOT_FOUND"


# ── AC-0006-14 and -15 ─ saldo and faltante with NFs ─────────────────────────


def test_AC_0006_14_the_quantity_saldo_ignores_the_nfs(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """The item's quantidade_disponivel is the NE ledger's, before and after an NF."""
    ata, items, ne = issued
    before = item_saldo(application, gestor, ata["id"], items[0]["id"])
    value = saldo(application, gestor, ata["id"])["valor_empenhado"]
    assert d(before["quantidade_disponivel"]) == 700
    launched(application, gestor, ne, "100", "1000.00")
    after = item_saldo(application, gestor, ata["id"], items[0]["id"])
    assert d(after["quantidade_disponivel"]) == 700
    assert saldo(application, gestor, ata["id"])["valor_empenhado"] == value


def test_AC_0006_15_faltante_counts_down_to_zero(
    application: TestClient, gestor: dict[str, str], issued: tuple
) -> None:
    """What the NE waits for drops with each NF, to nothing."""
    _, _, ne = issued
    launched(application, gestor, ne, "100", "1000.00")
    assert d(ne_line(application, gestor, ne["id"])["quantidade_faltante"]) == 200
    launched(application, gestor, ne, "200", "2000.00")
    assert d(ne_line(application, gestor, ne["id"])["quantidade_faltante"]) == 0
