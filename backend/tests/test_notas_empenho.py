"""The NE flow — SPEC-0004 v1.1.

Every cell of the transition table is asserted (RN08), and the saldo guard is
tested against two real connections meeting at a barrier (AC-0004-13).
"""

from __future__ import annotations

import decimal
import threading
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import clock
from app.models.user import User
from tests.catalogue import ATAS, add_item, audit_rows, grupo, item_of, login, make_ata, make_insumo

NES = "/api/v1/notas-empenho"
PROCESSO = "00301.000451/2026-12"
STAGES = ("demanda", "validacao_saldo", "pre_empenho", "envio_fornecedor", "ne_emitida")
ALL = (*STAGES, "cancelada")


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


def numero() -> str:
    """A número no other test uses."""
    return uuid.uuid4().hex[:12].upper()


def setup_ata(
    application: TestClient,
    gestor: dict[str, str],
    lines: list[tuple[str, str]],
    *,
    total: str = "100000.00",
    **override: object,
) -> tuple[dict, list[dict]]:
    """An ATA of `total` with one item per (quantity, unit price), and its items."""
    ata = make_ata(application, gestor, total_value=total, **override)
    raiz = grupo(application, gestor)
    items: list[dict] = []
    for quantity, price in lines:
        insumo = make_insumo(application, gestor, raiz["id"])
        listed = add_item(
            application, gestor, ata["id"], insumo["id"], quantity=quantity, unit_price=price
        )
        items.append(item_of(listed, insumo["id"]))
    return ata, items


def open_ne(
    application: TestClient,
    headers: dict[str, str],
    ata_id: str,
    lines: list[tuple[str, str]],
    processo: str = PROCESSO,
) -> object:
    """POST an NE; the raw response."""
    return application.post(
        NES,
        json={
            "ata_id": ata_id,
            "processo_sei": processo,
            "items": [{"item_ata_id": i, "quantity": q} for i, q in lines],
        },
        headers=headers,
    )


def advance(application: TestClient, headers: dict[str, str], ne_id: str, **body: object) -> object:
    """Advance one stage, sending the número the next stage needs."""
    return application.post(f"{NES}/{ne_id}/avancar", json=body, headers=headers)


def to_stage(application: TestClient, gestor: dict[str, str], ne_id: str, stage: str) -> dict:
    """Walk an NE from demanda to `stage`, or cancel it; the NE as it ends."""
    current = application.get(f"{NES}/{ne_id}", headers=gestor).json()
    if stage == "cancelada":
        response = application.post(
            f"{NES}/{ne_id}/cancelar", json={"justification": "Aberta por engano."}, headers=gestor
        )
        assert response.status_code == 200, response.text
        return response.json()
    while current["status"] != stage:
        nxt = STAGES[STAGES.index(current["status"]) + 1]
        body: dict[str, object] = {}
        if nxt == "pre_empenho":
            body["numero_pre_empenho"] = numero()
        if nxt == "ne_emitida":
            body["number"] = numero()
        response = advance(application, gestor, ne_id, **body)
        assert response.status_code == 200, response.text
        current = response.json()
    return current


def saldo(application: TestClient, headers: dict[str, str], ata_id: str) -> dict:
    """The ATA's value saldo."""
    response = application.get(f"{ATAS}/{ata_id}/saldo", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def item_saldo(application: TestClient, headers: dict[str, str], ata_id: str, item_id: str) -> dict:
    """One item's quantity saldo."""
    response = application.get(f"{ATAS}/{ata_id}/itens/saldo", headers=headers)
    assert response.status_code == 200, response.text
    return next(i for i in response.json()["items"] if i["item_ata_id"] == item_id)


def money(value: str) -> decimal.Decimal:
    """A decimal string as a Decimal."""
    return decimal.Decimal(value)


@pytest.fixture
def ne(application: TestClient, gestor: dict[str, str]) -> tuple[dict, list[dict], dict]:
    """An ATA of R$ 100.000,00 with two items, and an NE of R$ 30.000,00 in demanda."""
    ata, items = setup_ata(application, gestor, [("100", "200"), ("100", "100")])
    response = open_ne(
        application, gestor, ata["id"], [(items[0]["id"], "100"), (items[1]["id"], "100")]
    )
    assert response.status_code == 201, response.text
    return ata, items, response.json()


# ── §4.1 Opening ────────────────────────────────────────────────────────────


def test_ac_0004_01_opens_a_multi_item_ne(
    application: TestClient, gestor_user: tuple[dict, User], db_session: Session
) -> None:
    """AC-0004-01 — 10 notebooks and 5 monitors make R$ 84.000,00, in demanda, audited."""
    gestor, user = gestor_user
    ata, items = setup_ata(
        application, gestor, [("50", "7800"), ("20", "1200")], total="2840000.00"
    )

    response = open_ne(
        application, gestor, ata["id"], [(items[0]["id"], "10"), (items[1]["id"], "5")]
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "demanda"
    assert len(body["items"]) == 2
    assert money(body["value"]) == decimal.Decimal("84000.00")
    assert body["number"] is None and body["numero_pre_empenho"] is None
    rows = audit_rows(db_session, body["id"], "ne.criada")
    assert len(rows) == 1 and rows[0].usuario_id == user.id


def test_ac_0004_01_copies_the_price_and_rounds_once(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0004-01, ADR-0016 — 3 × 0,00599 is R$ 0,02 once, not three roundings."""
    ata, items = setup_ata(application, gestor, [("1000", "0.00599")])

    body = open_ne(application, gestor, ata["id"], [(items[0]["id"], "3")]).json()

    line = body["items"][0]
    assert money(line["unit_price"]) == decimal.Decimal("0.00599")
    assert money(line["value"]) == decimal.Decimal("0.02")


@pytest.mark.parametrize(
    ("case", "field"),
    [
        ("no_ata", "ata_id"),
        ("no_processo", "processo_sei"),
        ("empty_items", "items"),
        ("no_item_id", "items.0.item_ata_id"),
        ("no_quantity", "items.0.quantity"),
    ],
)
def test_ac_0004_02_rn09_mandatory_fields(
    application: TestClient,
    gestor: dict[str, str],
    ne: tuple,
    case: str,
    field: str,
    db_session: Session,
) -> None:
    """AC-0004-02 — each missing field is named, and nothing is written."""
    ata, items, _ = ne
    line: dict[str, object] = {"item_ata_id": items[0]["id"], "quantity": "1"}
    body: dict[str, object] = {"ata_id": ata["id"], "processo_sei": PROCESSO, "items": [line]}
    if case == "no_ata":
        body.pop("ata_id")
    elif case == "no_processo":
        body.pop("processo_sei")
    elif case == "empty_items":
        body["items"] = []
    elif case == "no_item_id":
        line.pop("item_ata_id")
    else:
        line.pop("quantity")
    before = db_session.execute(text("SELECT count(*) FROM nota_empenho")).scalar_one()

    response = application.post(NES, json=body, headers=gestor)

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "INVALID_DATA"
    assert field in error["fields"], error["fields"]
    db_session.rollback()
    assert db_session.execute(text("SELECT count(*) FROM nota_empenho")).scalar_one() == before


def test_ac_0004_03_processo_sei_format(application: TestClient, gestor: dict, ne: tuple) -> None:
    """AC-0004-03 — "12345" is refused, naming the format."""
    ata, items, _ = ne

    response = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")], processo="12345")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "PROCESSO_SEI_INVALIDO"
    assert "NNNNN.NNNNNN/AAAA-DD" in error["message"]


# ── §4.1 The state machine ──────────────────────────────────────────────────


def test_ac_0004_04_advances_one_stage(
    application: TestClient, gestor: dict, ne: tuple, db_session: Session
) -> None:
    """AC-0004-04 — demanda to validacao_saldo, with the prior status in the audit row."""
    response = advance(application, gestor, ne[2]["id"])

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "validacao_saldo"
    rows = audit_rows(db_session, ne[2]["id"], "ne.avancada")
    assert rows[-1].dados_anteriores["status"] == "demanda"


FORWARD = {(a, b) for a, b in zip(STAGES, STAGES[1:], strict=False)}
BACKWARD = {
    ("validacao_saldo", "demanda"),
    ("pre_empenho", "validacao_saldo"),
    ("envio_fornecedor", "pre_empenho"),
}
CANCELS = {(s, "cancelada") for s in STAGES if s != "ne_emitida"}


@pytest.mark.parametrize(("origem", "destino"), [(a, b) for a in ALL for b in ALL if a != b])
def test_ac_0004_05_rn08_every_cell_of_the_transition_table(
    application: TestClient, gestor: dict, origem: str, destino: str, db_session: Session
) -> None:
    """AC-0004-05, -10, -11 — the 30 cells: 4 forward, 3 back, 4 cancels, 19 refused."""
    ata, items = setup_ata(application, gestor, [("10", "10")])
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")]).json()["id"]
    to_stage(application, gestor, ne_id, origem)

    if destino == "cancelada":
        response = application.post(
            f"{NES}/{ne_id}/cancelar", json={"justification": "Teste."}, headers=gestor
        )
        allowed = (origem, destino) in CANCELS
    elif destino in STAGES and origem in STAGES and STAGES.index(destino) > STAGES.index(origem):
        body: dict[str, object] = {"to": destino}
        if destino == "pre_empenho":
            body["numero_pre_empenho"] = numero()
        if destino == "ne_emitida":
            body["number"] = numero()
        response = advance(application, gestor, ne_id, **body)
        allowed = (origem, destino) in FORWARD
    else:
        response = application.post(
            f"{NES}/{ne_id}/reverter",
            json={"to": destino, "justification": "Teste."},
            headers=gestor,
        )
        allowed = (origem, destino) in BACKWARD

    if allowed:
        assert response.status_code == 200, response.text
        assert response.json()["status"] == destino
    else:
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "TRANSICAO_INVALIDA"
        current = application.get(f"{NES}/{ne_id}", headers=gestor).json()
        assert current["status"] == origem
        blocked = audit_rows(db_session, ne_id, "ne.bloqueada")
        assert blocked[-1].dados_anteriores["motivo"] == "TRANSICAO_INVALIDA"


def test_ac_0004_06_rn03_reversal_and_cancellation_need_a_justification(
    application: TestClient, gestor: dict, ne: tuple
) -> None:
    """AC-0004-06 — no justification, 422 naming it, and the NE does not move."""
    ne_id = ne[2]["id"]
    to_stage(application, gestor, ne_id, "pre_empenho")

    for action in ("reverter", "cancelar"):
        for body in ({}, {"justification": "   "}):
            response = application.post(f"{NES}/{ne_id}/{action}", json=body, headers=gestor)
            assert response.status_code == 422, response.text
            error = response.json()["error"]
            assert error["code"] == "INVALID_DATA"
            assert "justification" in error["fields"]
    assert application.get(f"{NES}/{ne_id}", headers=gestor).json()["status"] == "pre_empenho"


def test_ac_0004_07_rn03_reversal_is_recorded(
    application: TestClient, gestor: dict, ne: tuple, db_session: Session
) -> None:
    """AC-0004-07 — back to validacao_saldo, justified, and the reserved saldo released."""
    ata, _, created = ne
    to_stage(application, gestor, created["id"], "pre_empenho")
    reserved = saldo(application, gestor, ata["id"])["valor_reservado"]

    response = application.post(
        f"{NES}/{created['id']}/reverter",
        json={"justification": "valor divergente da proposta"},
        headers=gestor,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "validacao_saldo"
    row = audit_rows(db_session, created["id"], "ne.revertida")[-1]
    assert row.justificativa == "valor divergente da proposta"
    assert row.dados_anteriores["status"] == "pre_empenho"
    assert money(reserved) == decimal.Decimal("30000.00")
    assert money(saldo(application, gestor, ata["id"])["valor_reservado"]) == 0


def test_ac_0004_08_servidor_advances_only(
    application: TestClient, gestor: dict, servidor: dict, ne: tuple, db_session: Session
) -> None:
    """AC-0004-08 — a servidor advances; opening, the itens, reversal and cancel are 403."""
    ata, items, created = ne
    ne_id = created["id"]

    moved = advance(application, servidor, ne_id)
    assert moved.status_code == 200 and moved.json()["status"] == "validacao_saldo"

    refused = [
        open_ne(application, servidor, ata["id"], [(items[0]["id"], "1")]),
        application.put(
            f"{NES}/{ne_id}/itens",
            json={"items": [{"item_ata_id": items[0]["id"], "quantity": "1"}]},
            headers=servidor,
        ),
        application.post(f"{NES}/{ne_id}/reverter", json={"justification": "x"}, headers=servidor),
        application.post(f"{NES}/{ne_id}/cancelar", json={"justification": "x"}, headers=servidor),
    ]
    for response in refused:
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"
    db_session.rollback()
    denials = db_session.execute(
        text(
            "SELECT count(*) FROM historico_movimentacao WHERE acao = 'auth.negada'"
            " AND dados_anteriores->>'rota' LIKE '/api/v1/notas-empenho%'"
            " AND dados_anteriores->>'perfil' = 'servidor'"
        )
    ).scalar_one()
    assert denials >= 4


def test_ac_0004_09_auditor_reads_only(
    application: TestClient, gestor: dict, auditor: dict, ne: tuple
) -> None:
    """AC-0004-09 — every write is 403 for the auditor; reading is 200."""
    ata, items, created = ne
    ne_id = created["id"]
    writes = [
        open_ne(application, auditor, ata["id"], [(items[0]["id"], "1")]),
        application.put(f"{NES}/{ne_id}/itens", json={"items": []}, headers=auditor),
        advance(application, auditor, ne_id),
        application.post(f"{NES}/{ne_id}/reverter", json={"justification": "x"}, headers=auditor),
        application.post(f"{NES}/{ne_id}/cancelar", json={"justification": "x"}, headers=auditor),
    ]
    for response in writes:
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"
    assert application.get(f"{NES}/{ne_id}", headers=auditor).status_code == 200


def test_ac_0004_10_reversal_is_one_step(application: TestClient, gestor: dict, ne: tuple) -> None:
    """AC-0004-10 — envio_fornecedor straight back to demanda is refused."""
    ne_id = ne[2]["id"]
    to_stage(application, gestor, ne_id, "envio_fornecedor")

    response = application.post(
        f"{NES}/{ne_id}/reverter", json={"to": "demanda", "justification": "x"}, headers=gestor
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TRANSICAO_INVALIDA"


def test_ac_0004_11_ne_emitida_is_terminal(
    application: TestClient, gestor: dict, ne: tuple
) -> None:
    """AC-0004-11 — nothing leaves ne_emitida, cancellation included."""
    ne_id = ne[2]["id"]
    to_stage(application, gestor, ne_id, "ne_emitida")

    for response in (
        advance(application, gestor, ne_id),
        application.post(f"{NES}/{ne_id}/reverter", json={"justification": "x"}, headers=gestor),
        application.post(f"{NES}/{ne_id}/cancelar", json={"justification": "x"}, headers=gestor),
    ):
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "TRANSICAO_INVALIDA"


# ── §4.2 The saldo guard ────────────────────────────────────────────────────


def test_ac_0004_12_rn10_insufficient_saldo_blocks(
    application: TestClient, gestor: dict, db_session: Session
) -> None:
    """AC-0004-12 — R$ 78.000,00 against R$ 50.000,00: 409, the figures named, nothing reserved."""
    ata, items = setup_ata(application, gestor, [("100", "780")], total="50000.00")
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "100")]).json()["id"]
    to_stage(application, gestor, ne_id, "validacao_saldo")

    response = advance(application, gestor, ne_id, numero_pre_empenho=numero())

    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "SALDO_INSUFICIENTE"
    assert "R$ 50.000,00" in error["message"] and "R$ 78.000,00" in error["message"]
    current = application.get(f"{NES}/{ne_id}", headers=gestor).json()
    assert current["status"] == "validacao_saldo" and current["numero_pre_empenho"] is None
    assert money(saldo(application, gestor, ata["id"])["valor_reservado"]) == 0
    blocked = audit_rows(db_session, ne_id, "ne.bloqueada")[-1]
    assert blocked.dados_anteriores["motivo"] == "SALDO_INSUFICIENTE"


def test_ac_0004_13_rn10_concurrent_advances(
    application: TestClient, gestor_user: tuple[dict, User], db_session: Session
) -> None:
    """AC-0004-13 — two NEs of R$ 60.000,00 on R$ 100.000,00, at once: exactly one passes."""
    from app.core.db import session_factory
    from app.services import notas_empenho as service
    from app.services.errors import SaldoInsuficiente

    gestor, user = gestor_user
    ata, items = setup_ata(
        application, gestor, [("100", "200"), ("100", "200"), ("100", "200")], total="100000.00"
    )
    ids = []
    for _ in range(2):
        lines = [(i["id"], "100") for i in items]
        ne_id = open_ne(application, gestor, ata["id"], lines).json()["id"]
        to_stage(application, gestor, ne_id, "validacao_saldo")
        ids.append(ne_id)

    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def run(ne_id: str) -> None:
        with session_factory()() as session:
            actor = session.get(User, user.id)
            assert actor is not None
            barrier.wait()
            try:
                service.advance(
                    session,
                    actor=actor,
                    ne_id=uuid.UUID(ne_id),
                    to=None,
                    numero_pre_empenho=numero(),
                    numero=None,
                    at=clock.now(),
                    correlation_id=uuid.uuid4(),
                )
                session.commit()
                outcomes.append("ok")
            except SaldoInsuficiente:
                session.rollback()
                outcomes.append("saldo")

    threads = [threading.Thread(target=run, args=(i,)) for i in ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(outcomes) == ["ok", "saldo"]
    assert money(saldo(application, gestor, ata["id"])["valor_reservado"]) == decimal.Decimal(
        "60000.00"
    )


def test_ac_0004_14_rn17_reserves_at_pre_empenho(
    application: TestClient, gestor: dict, ne: tuple
) -> None:
    """AC-0004-14 — R$ 30.000,00 reserved, none committed, R$ 70.000,00 left, and quantity."""
    ata, items, created = ne
    to_stage(application, gestor, created["id"], "pre_empenho")

    s = saldo(application, gestor, ata["id"])
    assert money(s["valor_reservado"]) == decimal.Decimal("30000.00")
    assert money(s["valor_empenhado"]) == 0
    assert money(s["saldo_disponivel"]) == decimal.Decimal("70000.00")
    assert (
        money(item_saldo(application, gestor, ata["id"], items[0]["id"])["quantidade_reservada"])
        == 100
    )


def test_ac_0004_15_rn17_commits_at_emission(
    application: TestClient, gestor: dict, ne: tuple
) -> None:
    """AC-0004-15 — reserved becomes committed; saldo disponível does not move."""
    ata, _, created = ne
    to_stage(application, gestor, created["id"], "ne_emitida")

    s = saldo(application, gestor, ata["id"])
    assert money(s["valor_reservado"]) == 0
    assert money(s["valor_empenhado"]) == decimal.Decimal("30000.00")
    assert money(s["saldo_disponivel"]) == decimal.Decimal("70000.00")


def test_ac_0004_16_cancellation_releases(
    application: TestClient, gestor: dict, ne: tuple, db_session: Session
) -> None:
    """AC-0004-16 — the value and every item's quantity return; the row says how much."""
    ata, items, created = ne
    to_stage(application, gestor, created["id"], "pre_empenho")

    response = application.post(
        f"{NES}/{created['id']}/cancelar",
        json={"justification": "Aberta por engano."},
        headers=gestor,
    )

    assert response.status_code == 200, response.text
    assert money(saldo(application, gestor, ata["id"])["saldo_disponivel"]) == decimal.Decimal(
        "100000.00"
    )
    for item in items:
        assert (
            money(item_saldo(application, gestor, ata["id"], item["id"])["quantidade_reservada"])
            == 0
        )
    row = audit_rows(db_session, created["id"], "ne.cancelada")[-1]
    assert row.justificativa == "Aberta por engano."
    assert money(row.dados_anteriores["valor_liberado"]) == decimal.Decimal("30000.00")


def test_ac_0004_16_cancelling_in_demanda_releases_nothing(
    application: TestClient, gestor: dict, ne: tuple, db_session: Session
) -> None:
    """AC-0004-16 — an NE that reserved nothing records valor_liberado R$ 0,00."""
    to_stage(application, gestor, ne[2]["id"], "cancelada")

    row = audit_rows(db_session, ne[2]["id"], "ne.cancelada")[-1]
    assert money(row.dados_anteriores["valor_liberado"]) == 0


# ── §4.3 ATA eligibility and locks ──────────────────────────────────────────


@pytest.mark.parametrize(
    "reason", ["vencida", "não iniciada", "suspensa", "encerrada", "cancelada"]
)
def test_ac_0004_17_rn11_ineligible_ata(application: TestClient, gestor: dict, reason: str) -> None:
    """AC-0004-17 — each reason refuses the NE and is named; the ATA's history still reads."""
    dates = {
        "vencida": {"vigencia_inicio": "2020-01-01", "vigencia_fim": "2021-01-01"},
        "não iniciada": {"vigencia_inicio": "2031-01-01", "vigencia_fim": "2032-01-01"},
    }.get(reason, {})
    ata, items = setup_ata(application, gestor, [("10", "10")], **dates)
    move = {"suspensa": "suspender", "encerrada": "encerrar", "cancelada": "cancelar"}.get(reason)
    if move:
        moved = application.post(
            f"{ATAS}/{ata['id']}/{move}", json={"justification": "Teste."}, headers=gestor
        )
        assert moved.status_code == 200, moved.text

    response = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")])

    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "ATA_NAO_ELEGIVEL"
    assert reason in error["message"]
    assert application.get(f"{ATAS}/{ata['id']}", headers=gestor).status_code == 200


def test_ac_0004_25_rn13_ata_with_ne_in_progress_is_not_closed(
    application: TestClient, gestor: dict, ne: tuple
) -> None:
    """AC-0004-25 — closing is refused naming the NE; once it is issued, it closes."""
    ata, _, created = ne

    response = application.post(
        f"{ATAS}/{ata['id']}/encerrar", json={"justification": "Fim."}, headers=gestor
    )

    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "ATA_COM_NE_PENDENTE"
    assert PROCESSO in error["message"]
    assert application.get(f"{ATAS}/{ata['id']}", headers=gestor).json()["status"] == "vigente"
    to_stage(application, gestor, created["id"], "ne_emitida")
    closed = application.post(
        f"{ATAS}/{ata['id']}/encerrar", json={"justification": "Fim."}, headers=gestor
    )
    assert closed.status_code == 200, closed.text


@pytest.mark.parametrize(
    "change",
    [
        {"number": "OUTRA-ATA"},
        {"vigencia_fim": "2031-12-31"},
        {"total_value": "200000.00"},
        {"budget_date": "2026-04-01"},
    ],
)
def test_ac_0004_26_ne_emitida_locks_the_ata(
    application: TestClient, gestor: dict, ne: tuple, change: dict
) -> None:
    """AC-0004-26 — the figures are refused once an NE is issued; the objeto is not."""
    ata, _, created = ne
    to_stage(application, gestor, created["id"], "ne_emitida")
    if "number" in change:
        change = {"number": f"OUTRA-{uuid.uuid4().hex[:8]}"}

    response = application.patch(f"{ATAS}/{ata['id']}", json=change, headers=gestor)

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "ATA_NAO_EDITAVEL"
    other = application.patch(f"{ATAS}/{ata['id']}", json={"subject": "Corrigido"}, headers=gestor)
    assert other.status_code == 200, other.text


def test_ac_0004_27_item_with_ne_locks(application: TestClient, gestor: dict, ne: tuple) -> None:
    """AC-0004-27 — past demanda, the item's quantity, price and removal are refused."""
    ata, items, created = ne
    item_id = items[0]["id"]
    edited = application.patch(
        f"{ATAS}/{ata['id']}/itens/{item_id}", json={"quantity": "120"}, headers=gestor
    )
    assert edited.status_code == 200, edited.text  # an NE in demanda locks nothing

    to_stage(application, gestor, created["id"], "validacao_saldo")
    for response in (
        application.patch(
            f"{ATAS}/{ata['id']}/itens/{item_id}", json={"quantity": "130"}, headers=gestor
        ),
        application.patch(
            f"{ATAS}/{ata['id']}/itens/{item_id}", json={"unit_price": "250"}, headers=gestor
        ),
        application.post(f"{ATAS}/{ata['id']}/itens/{item_id}/remover", headers=gestor),
    ):
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "ITEM_ATA_COM_NE"

    to_stage(application, gestor, created["id"], "cancelada")
    released = application.patch(
        f"{ATAS}/{ata['id']}/itens/{item_id}", json={"quantity": "130"}, headers=gestor
    )
    assert released.status_code == 200, released.text


# ── §4.4 Counters ───────────────────────────────────────────────────────────


def test_ac_0004_18_stage_counters(application: TestClient, gestor: dict) -> None:
    """AC-0004-18 — +1 emitida, +4 em andamento, +1 cancelada: +6 in total."""
    before = application.get(f"{NES}/indicadores", headers=gestor).json()
    ata, items = setup_ata(application, gestor, [("100", "10")])
    targets = [
        "ne_emitida",
        "demanda",
        "validacao_saldo",
        "pre_empenho",
        "envio_fornecedor",
        "cancelada",
    ]
    for stage in targets:
        ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")]).json()["id"]
        to_stage(application, gestor, ne_id, stage)

    after = application.get(f"{NES}/indicadores", headers=gestor).json()

    assert after["emitidas"] - before["emitidas"] == 1
    assert after["em_andamento"] - before["em_andamento"] == 4
    assert after["total"] - before["total"] == 6


# ── §4.5 Item composition ───────────────────────────────────────────────────


def test_ac_0004_19_ne_may_not_be_emptied(application: TestClient, gestor: dict, ne: tuple) -> None:
    """AC-0004-19 — an empty list is NE_SEM_ITENS and the itens stay."""
    response = application.put(f"{NES}/{ne[2]['id']}/itens", json={"items": []}, headers=gestor)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NE_SEM_ITENS"
    assert len(application.get(f"{NES}/{ne[2]['id']}", headers=gestor).json()["items"]) == 2


def test_ac_0004_19_replacing_the_itens_is_audited(
    application: TestClient, gestor: dict, ne: tuple, db_session: Session
) -> None:
    """§8 — ne.itens_alterados keeps the list it replaced."""
    _, items, created = ne

    response = application.put(
        f"{NES}/{created['id']}/itens",
        json={"items": [{"item_ata_id": items[0]["id"], "quantity": "5"}]},
        headers=gestor,
    )

    assert response.status_code == 200, response.text
    assert money(response.json()["value"]) == decimal.Decimal("1000.00")
    row = audit_rows(db_session, created["id"], "ne.itens_alterados")[-1]
    assert len(row.dados_anteriores["itens"]) == 2


def test_ac_0004_20_same_item_twice(
    application: TestClient, gestor: dict, ne: tuple, db_session: Session
) -> None:
    """AC-0004-20 — the duplicate insumo is named and no NE is created."""
    ata, items, _ = ne
    before = db_session.execute(text("SELECT count(*) FROM nota_empenho")).scalar_one()

    response = open_ne(
        application, gestor, ata["id"], [(items[0]["id"], "1"), (items[0]["id"], "2")]
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "ITEM_DUPLICADO"
    db_session.rollback()
    assert db_session.execute(text("SELECT count(*) FROM nota_empenho")).scalar_one() == before


def test_ac_0004_21_item_of_another_ata(application: TestClient, gestor: dict, ne: tuple) -> None:
    """AC-0004-21 — an item of another ATA is refused, naming that ATA."""
    ata, _, _ = ne
    other, other_items = setup_ata(application, gestor, [("10", "10")])

    response = open_ne(application, gestor, ata["id"], [(other_items[0]["id"], "1")])

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "ITEM_DE_OUTRA_ATA"
    assert other["number"] in error["message"]


def test_ac_0004_22_itens_frozen_from_pre_empenho(
    application: TestClient, gestor: dict, ne: tuple
) -> None:
    """AC-0004-22 — from pré-empenho the itens are frozen and stay as they were."""
    _, items, created = ne
    to_stage(application, gestor, created["id"], "pre_empenho")

    response = application.put(
        f"{NES}/{created['id']}/itens",
        json={"items": [{"item_ata_id": items[0]["id"], "quantity": "1"}]},
        headers=gestor,
    )

    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "NE_ITENS_CONGELADOS"
    assert "Cancele a NE" in error["message"]
    assert len(application.get(f"{NES}/{created['id']}", headers=gestor).json()["items"]) == 2


def test_ac_0004_23_price_snapshot(
    application: TestClient, gestor: dict, ne: tuple, db_session: Session, admin_connection: object
) -> None:
    """AC-0004-23 — a later price on the ITEM_ATA leaves the NE's line alone."""
    _, items, created = ne
    admin_connection.execute(  # type: ignore[attr-defined]
        "UPDATE item_ata SET valor_unitario = 999 WHERE id = %s", (items[0]["id"],)
    )

    body = application.get(f"{NES}/{created['id']}", headers=gestor).json()

    assert money(body["value"]) == decimal.Decimal("30000.00")


def test_ac_0004_24_rn10_quantity_exhaustion(application: TestClient, gestor: dict) -> None:
    """AC-0004-24 — 5 monitors of 3 left are refused though the money is there."""
    ata, items = setup_ata(application, gestor, [("3", "1200")], total="500000.00")
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "5")]).json()["id"]
    to_stage(application, gestor, ne_id, "validacao_saldo")

    response = advance(application, gestor, ne_id, numero_pre_empenho=numero())

    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "QUANTIDADE_INSUFICIENTE"
    assert "Disponível: 3" in error["message"] and "Necessário: 5" in error["message"]
    assert application.get(f"{NES}/{ne_id}", headers=gestor).json()["status"] == "validacao_saldo"


# ── §9 The números ──────────────────────────────────────────────────────────


def test_ac_0004_28_numero_at_emission(application: TestClient, gestor: dict, ne: tuple) -> None:
    """AC-0004-28 — required at emission, stored as typed, and unique."""
    ata, items, created = ne
    to_stage(application, gestor, created["id"], "envio_fornecedor")

    missing = advance(application, gestor, created["id"])
    assert missing.status_code == 422
    assert "number" in missing.json()["error"]["fields"]

    typed = numero()
    issued = advance(application, gestor, created["id"], number=typed)
    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] == "ne_emitida" and issued.json()["number"] == typed
    assert issued.json()["issued_on"] is not None

    other, other_items = setup_ata(application, gestor, [("10", "10")])
    second = open_ne(application, gestor, other["id"], [(other_items[0]["id"], "1")]).json()["id"]
    to_stage(application, gestor, second, "envio_fornecedor")
    duplicate = advance(application, gestor, second, number=typed)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "NE_DUPLICADA"


def test_ac_0004_29_nota_de_pre_empenho(
    application: TestClient, gestor: dict, ne: tuple, db_session: Session
) -> None:
    """AC-0004-29 — required on entering pré-empenho, unique, and cleared by a reversal."""
    ata, items, created = ne
    to_stage(application, gestor, created["id"], "validacao_saldo")

    missing = advance(application, gestor, created["id"])
    assert missing.status_code == 422
    assert "numero_pre_empenho" in missing.json()["error"]["fields"]

    typed = numero()
    moved = advance(application, gestor, created["id"], numero_pre_empenho=typed)
    assert moved.status_code == 200, moved.text
    assert moved.json()["numero_pre_empenho"] == typed

    second = open_ne(application, gestor, ata["id"], [(items[1]["id"], "1")]).json()["id"]
    to_stage(application, gestor, second, "validacao_saldo")
    duplicate = advance(application, gestor, second, numero_pre_empenho=typed)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "PRE_EMPENHO_DUPLICADO"

    back = application.post(
        f"{NES}/{created['id']}/reverter", json={"justification": "Recusado."}, headers=gestor
    )
    assert back.json()["numero_pre_empenho"] is None
    row = audit_rows(db_session, created["id"], "ne.revertida")[-1]
    assert row.dados_anteriores["numero_pre_empenho"] == typed


def test_an_unknown_ne_is_404(application: TestClient, gestor: dict) -> None:
    """§5 — NOT_FOUND."""
    response = application.get(f"{NES}/{uuid.uuid4()}", headers=gestor)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
