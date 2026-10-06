"""ATAs — SPEC-0002 v1.0, AC-0002-01 to -25 (minus the deferred ones).

AC-0002-11, -12 and the saldo and quantity parts of -13 and -14 are deferred to
SPEC-0003, SPEC-0004 and SPEC-0006 (SPEC-0002 §3) and have no test here.

The shared test database holds other tests' ATAs, so a test that reads a list or
an alert looks only at the ATAs it created.
"""

from __future__ import annotations

import datetime
import decimal
import socket
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user import User

ATAS = "/api/v1/atas"
LOGIN = "/api/v1/auth/login"
# Not `*_PASSWORD`: gitleaks reads that keyword beside this entropy as a credential.
LONG_ENOUGH = "SenhaLongaOSuficiente-2026"

CNPJ = "11.222.333/0001-81"
OTHER_CNPJ = "45.723.174/0001-10"
PROCESSO = "12345.123456/2026-12"


def _login(
    application: TestClient, create_user: Callable[..., User], perfil: str
) -> dict[str, str]:
    email = f"{perfil}-{uuid.uuid4().hex[:8]}@sc.gov.br"
    create_user(email=email, perfil=perfil, password=LONG_ENOUGH)
    entry = application.post(LOGIN, json={"email": email, "password": LONG_ENOUGH})
    assert entry.status_code == 200, entry.text
    return {"Authorization": f"Bearer {entry.json()['access_token']}"}


@pytest.fixture
def gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in gestor."""
    return _login(application, create_user, "gestor")


def body(**override: object) -> dict[str, object]:
    """A valid ATA registration, with whatever the test wants different."""
    data: dict[str, object] = {
        "number": f"ATA-{uuid.uuid4().hex[:10]}",
        "subject": "Material de expediente",
        "organ": "Secretaria de Saúde",
        "fornecedor": {"cnpj": CNPJ, "legal_name": "Papelaria Exemplo Ltda"},
        "vigencia_inicio": "2026-01-01",
        "vigencia_fim": "2026-12-31",
        "total_value": "100000.00",
        "budget_date": "2026-03-10",
    }
    data.update(override)
    return data


def make(
    application: TestClient, headers: dict[str, str], *, activate: bool = False, **override: object
) -> dict:
    """Register an ATA through the API, and activate it when asked."""
    response = application.post(ATAS, json=body(**override), headers=headers)
    assert response.status_code == 201, response.text
    ata = response.json()
    if activate:
        moved = application.post(f"{ATAS}/{ata['id']}/ativar", headers=headers)
        assert moved.status_code == 200, moved.text
        ata = moved.json()
    return ata


def audit_rows(db_session: Session, ata_id: str, acao: str | None = None) -> list:
    """The audit rows of an ATA, oldest first."""
    db_session.rollback()
    sql = (
        "SELECT acao, usuario_id, dados_anteriores, justificativa, ocorrido_em"
        " FROM historico_movimentacao WHERE entidade_id = :i"
    )
    params: dict[str, object] = {"i": ata_id}
    if acao:
        sql += " AND acao = :a"
        params["a"] = acao
    return list(db_session.execute(text(sql + " ORDER BY ocorrido_em"), params).all())


def freeze(monkeypatch: pytest.MonkeyPatch, day: str) -> None:
    """Put the application's clock at noon, Brasília time, on `day`."""
    instant = datetime.datetime.fromisoformat(f"{day}T15:00:00+00:00")
    monkeypatch.setattr("app.core.clock.now", lambda: instant)


# ── AC-0002-01 to -05 — registering ─────────────────────────────────────────


def test_ac_0002_01_a_gestor_registers_an_ata(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0002-01 — 201, `rascunho`, the gestor as responsavel, and an audit row."""
    response = application.post(ATAS, json=body(), headers=gestor)

    assert response.status_code == 201, response.text
    ata = response.json()
    assert ata["status"] == "rascunho"
    assert ata["fornecedor"]["cnpj"] == "11222333000181"
    assert decimal.Decimal(ata["total_value"]) == decimal.Decimal("100000.00")
    rows = audit_rows(db_session, ata["id"], "ata.criada")
    assert len(rows) == 1
    assert rows[0].dados_anteriores is None
    owner = db_session.execute(
        text("SELECT responsavel_id::text FROM ata WHERE id = :i"), {"i": ata["id"]}
    ).scalar_one()
    assert owner == str(rows[0].usuario_id) == ata["owner_id"]


@pytest.mark.parametrize(
    "missing", ["number", "subject", "organ", "vigencia_inicio", "budget_date"]
)
def test_ac_0002_01_a_missing_field_is_refused_by_name(
    application: TestClient, gestor: dict[str, str], db_session: Session, missing: str
) -> None:
    """AC-0002-01, RF11 — 422 `INVALID_DATA` naming the field, and nothing is created."""
    data = body()
    del data[missing]

    response = application.post(ATAS, json=data, headers=gestor)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_DATA"
    assert missing in error["fields"]


def test_ac_0002_02_the_numero_is_unique(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0002-02 — a duplicate answers 409 `ATA_DUPLICADA` and creates nothing."""
    first = make(application, gestor)

    response = application.post(ATAS, json=body(number=first["number"]), headers=gestor)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ATA_DUPLICADA"
    db_session.rollback()
    count = db_session.execute(
        text("SELECT count(*) FROM ata WHERE numero = :n"), {"n": first["number"]}
    ).scalar_one()
    assert count == 1


@pytest.mark.parametrize("fim", ["2026-01-01", "2025-12-31"])
def test_ac_0002_03_the_vigencia_is_a_real_interval(
    application: TestClient, gestor: dict[str, str], fim: str
) -> None:
    """AC-0002-03 — a fim that is not after the inicio is refused, naming vigencia_fim."""
    response = application.post(ATAS, json=body(vigencia_fim=fim), headers=gestor)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DATA"
    assert "vigencia_fim" in response.json()["error"]["fields"]


@pytest.mark.parametrize("value", ["0", "-5.00", "100.001", "1234567890123456"])
def test_ac_0002_04_the_valor_is_positive_and_exact(
    application: TestClient, gestor: dict[str, str], db_session: Session, value: str
) -> None:
    """AC-0002-04 — zero, negative, a third decimal or too many digits are refused, not rounded."""
    number = f"ATA-{uuid.uuid4().hex[:10]}"

    response = application.post(ATAS, json=body(number=number, total_value=value), headers=gestor)

    assert response.status_code == 422
    assert "total_value" in response.json()["error"]["fields"]
    db_session.rollback()
    assert (
        db_session.execute(
            text("SELECT count(*) FROM ata WHERE numero = :n"), {"n": number}
        ).scalar_one()
        == 0
    )


def test_ac_0002_04_a_valor_with_two_decimals_is_stored_exactly(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0002-04 — money is `Decimal` end to end (RNF15)."""
    ata = make(application, gestor, total_value="1234.56")
    assert ata["total_value"] == "1234.56"


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0002_05_only_a_gestor_writes(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    db_session: Session,
    perfil: str,
) -> None:
    """AC-0002-05 — every write answers 403 `PERFIL_NAO_AUTORIZADO` and changes nothing."""
    ata = make(application, gestor, activate=True)
    headers = _login(application, create_user, perfil)
    number = f"ATA-{uuid.uuid4().hex[:10]}"
    calls = [
        ("POST", ATAS, body(number=number)),
        ("PATCH", f"{ATAS}/{ata['id']}", {"subject": "Outro objeto"}),
        ("POST", f"{ATAS}/{ata['id']}/suspender", None),
        ("POST", f"{ATAS}/{ata['id']}/encerrar", None),
        ("POST", f"{ATAS}/{ata['id']}/cancelar", {"justification": "x"}),
        (
            "POST",
            f"{ATAS}/{ata['id']}/aditivos",
            {"kind": "prazo", "nova_vigencia_fim": "2027-06-30", "justification": "x"},
        ),
        (
            "POST",
            f"{ATAS}/{ata['id']}/reajustes",
            {"processo_sei": PROCESSO, "requested_on": "2026-03-10"},
        ),
    ]

    for method, path, payload in calls:
        response = application.request(method, path, json=payload, headers=headers)
        assert response.status_code == 403, f"{method} {path}: {response.text}"
        assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"

    db_session.rollback()
    row = db_session.execute(
        text("SELECT status, objeto FROM ata WHERE id = :i"), {"i": ata["id"]}
    ).one()
    assert (row.status, row.objeto) == ("vigente", "Material de expediente")
    assert (
        db_session.execute(
            text("SELECT count(*) FROM ata WHERE numero = :n"), {"n": number}
        ).scalar_one()
        == 0
    )
    # The denial is audited as AC-0001-18 requires.
    assert (
        db_session.execute(
            text("SELECT count(*) FROM historico_movimentacao WHERE acao = 'auth.negada'")
        ).scalar_one()
        >= 1
    )


# ── AC-0002-25 — the fornecedor ─────────────────────────────────────────────


def test_ac_0002_25_a_fornecedor_is_created_by_its_cnpj_and_then_reused(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0002-25 — one row per CNPJ, whatever the punctuation; the razão social is kept."""
    first = make(
        application,
        gestor,
        fornecedor={"cnpj": OTHER_CNPJ, "legal_name": "Primeira Razão Social"},
    )
    second = make(
        application,
        gestor,
        fornecedor={"cnpj": "45723174000110", "legal_name": "Outro Nome Qualquer"},
    )

    assert first["fornecedor"]["id"] == second["fornecedor"]["id"]
    assert second["fornecedor"]["legal_name"] == "Primeira Razão Social"
    db_session.rollback()
    assert (
        db_session.execute(
            text("SELECT count(*) FROM fornecedor WHERE cnpj = '45723174000110'")
        ).scalar_one()
        == 1
    )


@pytest.mark.parametrize("bad", ["11.222.333/0001-80", "123", "00000000000000", "abcdefghijklmn"])
def test_ac_0002_25_a_bad_cnpj_is_refused_and_creates_nothing(
    application: TestClient, gestor: dict[str, str], db_session: Session, bad: str
) -> None:
    """AC-0002-25 — malformed, wrong check digits or all equal: 422 naming fornecedor.cnpj."""
    number = f"ATA-{uuid.uuid4().hex[:10]}"

    response = application.post(
        ATAS,
        json=body(number=number, fornecedor={"cnpj": bad, "legal_name": "Empresa Inventada"}),
        headers=gestor,
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_DATA"
    assert "fornecedor.cnpj" in error["fields"]
    db_session.rollback()
    assert (
        db_session.execute(
            text("SELECT count(*) FROM ata WHERE numero = :n"), {"n": number}
        ).scalar_one()
        == 0
    )
    assert (
        db_session.execute(
            text("SELECT count(*) FROM fornecedor WHERE razao_social = 'Empresa Inventada'")
        ).scalar_one()
        == 0
    )


# ── AC-0002-23 — reading ────────────────────────────────────────────────────


@pytest.mark.parametrize("perfil", ["gestor", "servidor", "auditor"])
def test_ac_0002_23_every_perfil_reads_atas(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    perfil: str,
) -> None:
    """AC-0002-23 — a page with status and situacao_vigencia; the detail with its history."""
    ata = make(application, gestor, activate=True)
    headers = _login(application, create_user, perfil)

    page = application.get(f"{ATAS}?size=100", headers=headers)
    detail = application.get(f"{ATAS}/{ata['id']}", headers=headers)

    assert page.status_code == 200
    assert set(page.json()) == {"items", "total", "page", "size"}
    mine = [i for i in page.json()["items"] if i["id"] == ata["id"]]
    assert mine and mine[0]["status"] == "vigente"
    assert mine[0]["situacao_vigencia"] in {"vigente", "a_vencer", "vencida"}
    assert detail.status_code == 200
    assert detail.json()["aditivos"] == [] and detail.json()["reajustes"] == []


def test_ac_0002_23_an_unknown_id_is_404(application: TestClient, gestor: dict[str, str]) -> None:
    """AC-0002-23 — the generic `NOT_FOUND`."""
    response = application.get(f"{ATAS}/{uuid.uuid4()}", headers=gestor)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_ac_0002_23_the_list_filters_by_status_and_by_situacao_vigencia(
    application: TestClient, gestor: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-0002-23 — both filters, against a frozen clock."""
    freeze(monkeypatch, "2026-06-01")
    vigente = make(application, gestor, activate=True, vigencia_fim="2026-12-31")
    a_vencer = make(application, gestor, activate=True, vigencia_fim="2026-07-15")
    vencida = make(application, gestor, vigencia_fim="2026-05-31")

    def ids(query: str) -> set[str]:
        page = application.get(f"{ATAS}?size=100&{query}", headers=gestor).json()
        return {i["id"] for i in page["items"]}

    mine = {vigente["id"], a_vencer["id"], vencida["id"]}
    assert ids("situacao_vigencia=vigente") & mine == {vigente["id"]}
    assert ids("situacao_vigencia=a_vencer") & mine == {a_vencer["id"]}
    assert ids("situacao_vigencia=vencida") & mine == {vencida["id"]}
    assert ids("status=rascunho") & mine == {vencida["id"]}
    assert ids("status=vigente") & mine == {vigente["id"], a_vencer["id"]}


# ── AC-0002-24 — editing ────────────────────────────────────────────────────


def test_ac_0002_24_a_draft_is_editable_and_the_prior_values_are_audited(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0002-24 — everything while `rascunho`; the audit row keys are columns."""
    ata = make(application, gestor)

    response = application.patch(
        f"{ATAS}/{ata['id']}",
        json={"total_value": "120000.00", "vigencia_fim": "2027-01-31", "subject": "Novo objeto"},
        headers=gestor,
    )

    assert response.status_code == 200, response.text
    assert response.json()["subject"] == "Novo objeto"
    row = audit_rows(db_session, ata["id"], "ata.editada")[0]
    assert row.dados_anteriores == {
        "valor_total": "100000.00",
        "vigencia_fim": "2026-12-31",
        "objeto": "Material de expediente",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("number", "OUTRO-NUMERO"),
        ("vigencia_inicio", "2026-02-01"),
        ("vigencia_fim", "2027-02-01"),
        ("total_value", "1.00"),
        ("budget_date", "2026-04-01"),
        ("issued_on", "2026-01-02"),
        ("fornecedor", {"cnpj": OTHER_CNPJ, "legal_name": "Outra Empresa Ltda"}),
    ],
)
def test_ac_0002_24_the_figures_are_locked_after_activation(
    application: TestClient, gestor: dict[str, str], db_session: Session, field: str, value: object
) -> None:
    """AC-0002-24 — 409 `ATA_NAO_EDITAVEL`, and nothing changes."""
    ata = make(application, gestor, activate=True)

    response = application.patch(f"{ATAS}/{ata['id']}", json={field: value}, headers=gestor)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ATA_NAO_EDITAVEL"
    assert application.get(f"{ATAS}/{ata['id']}", headers=gestor).json()["number"] == ata["number"]
    assert audit_rows(db_session, ata["id"], "ata.editada") == []


def test_ac_0002_24_objeto_and_orgao_stay_editable_after_activation(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0002-24 — what is not a figure can still be corrected."""
    ata = make(application, gestor, activate=True)

    response = application.patch(
        f"{ATAS}/{ata['id']}", json={"subject": "Corrigido", "organ": "Outro órgão"}, headers=gestor
    )

    assert response.status_code == 200
    assert (response.json()["subject"], response.json()["organ"]) == ("Corrigido", "Outro órgão")


# ── AC-0002-22, -10, -17 — the lifecycle ────────────────────────────────────

VALID_MOVES = [
    ("rascunho", "ativar", "vigente"),
    ("vigente", "suspender", "suspensa"),
    ("suspensa", "retomar", "vigente"),
    ("vigente", "encerrar", "encerrada"),
    ("suspensa", "encerrar", "encerrada"),
    ("rascunho", "cancelar", "cancelada"),
    ("vigente", "cancelar", "cancelada"),
    ("suspensa", "cancelar", "cancelada"),
]
ALL_MOVES = ("ativar", "suspender", "retomar", "encerrar", "cancelar")


def _reach(application: TestClient, headers: dict[str, str], status: str) -> dict:
    """An ATA in the given status, by the shortest legitimate path."""
    path = {
        "rascunho": [],
        "vigente": ["ativar"],
        "suspensa": ["ativar", "suspender"],
        "encerrada": ["ativar", "encerrar"],
        "cancelada": ["cancelar"],
    }[status]
    ata = make(application, headers)
    for step in path:
        payload = {"justification": "Motivo."} if step == "cancelar" else None
        response = application.post(f"{ATAS}/{ata['id']}/{step}", json=payload, headers=headers)
        assert response.status_code == 200, response.text
    return ata


@pytest.mark.parametrize("origin,move,destination", VALID_MOVES)
def test_ac_0002_22_every_valid_move_changes_the_status_and_is_audited(
    application: TestClient,
    gestor: dict[str, str],
    db_session: Session,
    origin: str,
    move: str,
    destination: str,
) -> None:
    """AC-0002-22 — the eight moves the lifecycle allows."""
    ata = _reach(application, gestor, origin)
    payload = {"justification": "Motivo da ata."} if move == "cancelar" else None

    response = application.post(f"{ATAS}/{ata['id']}/{move}", json=payload, headers=gestor)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == destination
    acao = {
        "ativar": "ata.ativada",
        "suspender": "ata.suspensa",
        "retomar": "ata.retomada",
        "encerrar": "ata.encerrada",
        "cancelar": "ata.cancelada",
    }[move]
    rows = audit_rows(db_session, ata["id"], acao)
    assert len(rows) == 1
    assert rows[0].dados_anteriores == {"status": origin}
    assert rows[0].justificativa == ("Motivo da ata." if move == "cancelar" else None)


INVALID_MOVES = [
    (origin, move)
    for origin in ("rascunho", "vigente", "suspensa", "encerrada", "cancelada")
    for move in ALL_MOVES
    if not any(o == origin and m == move for o, m, _ in VALID_MOVES)
]


@pytest.mark.parametrize("origin,move", INVALID_MOVES)
def test_ac_0002_22_every_other_move_is_refused(
    application: TestClient, gestor: dict[str, str], origin: str, move: str
) -> None:
    """AC-0002-22 — 409 `TRANSICAO_INVALIDA`, the status unchanged, out of a terminal state too."""
    ata = _reach(application, gestor, origin)
    payload = {"justification": "x"} if move == "cancelar" else None

    response = application.post(f"{ATAS}/{ata['id']}/{move}", json=payload, headers=gestor)

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "TRANSICAO_INVALIDA"
    assert application.get(f"{ATAS}/{ata['id']}", headers=gestor).json()["status"] == origin


def test_ac_0002_22_cancelling_needs_a_justification(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0002-22 — no justification, no cancellation (RN03)."""
    ata = make(application, gestor)
    for payload in ({}, {"justification": ""}, {"justification": "  "}):
        response = application.post(f"{ATAS}/{ata['id']}/cancelar", json=payload, headers=gestor)
        assert response.status_code == 422
        assert "justification" in response.json()["error"]["fields"]
    assert application.get(f"{ATAS}/{ata['id']}", headers=gestor).json()["status"] == "rascunho"


def test_ac_0002_10_closing_records_who_and_when(
    application: TestClient,
    gestor: dict[str, str],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-0002-10 — the audit row carries the gestor and the time."""
    ata = make(application, gestor, activate=True)
    freeze(monkeypatch, "2026-08-20")

    response = application.post(f"{ATAS}/{ata['id']}/encerrar", headers=gestor)

    assert response.status_code == 200
    row = audit_rows(db_session, ata["id"], "ata.encerrada")[0]
    assert row.usuario_id is not None
    assert row.ocorrido_em == datetime.datetime(2026, 8, 20, 15, 0, tzinfo=datetime.UTC)


def test_ac_0002_17_an_ata_is_never_deleted(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0002-17 — DELETE answers 405; the missing DELETE privilege is in the migration test."""
    ata = make(application, gestor)

    response = application.delete(f"{ATAS}/{ata['id']}", headers=gestor)

    assert response.status_code == 405
    assert application.get(f"{ATAS}/{ata['id']}", headers=gestor).status_code == 200


# ── AC-0002-15, -09 — vigência and the renewal alert ────────────────────────


def test_ac_0002_15_situacao_vigencia_is_derived_at_read_time(
    application: TestClient,
    gestor: dict[str, str],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-0002-15 — three dates, the same row, no write between the reads."""
    ata = make(application, gestor, activate=True, vigencia_fim="2026-12-31")
    before = audit_rows(db_session, ata["id"])
    updated = db_session.execute(
        text("SELECT atualizado_em FROM ata WHERE id = :i"), {"i": ata["id"]}
    ).scalar_one()

    seen = []
    for day in ("2026-06-01", "2026-12-15", "2027-01-15"):
        freeze(monkeypatch, day)
        seen.append(
            application.get(f"{ATAS}/{ata['id']}", headers=gestor).json()["situacao_vigencia"]
        )

    assert seen == ["vigente", "a_vencer", "vencida"]
    assert audit_rows(db_session, ata["id"]) == before
    db_session.rollback()
    assert (
        db_session.execute(
            text("SELECT atualizado_em FROM ata WHERE id = :i"), {"i": ata["id"]}
        ).scalar_one()
        == updated
    )
    columns = {
        r[0]
        for r in db_session.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'ata'")
        )
    }
    assert "situacao_vigencia" not in columns


def test_ac_0002_09_the_renewal_alert_lists_the_ending_atas_soonest_first(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-0002-09 — within 90 days, no aditivo de prazo, ordered by days remaining."""
    freeze(monkeypatch, "2026-06-01")
    late = make(application, gestor, activate=True, vigencia_fim="2026-08-15")
    soon = make(application, gestor, activate=True, vigencia_fim="2026-06-20")
    far = make(application, gestor, activate=True, vigencia_fim="2027-06-01")
    draft = make(application, gestor, vigencia_fim="2026-06-25")
    extended = make(application, gestor, activate=True, vigencia_fim="2026-07-01")
    application.post(
        f"{ATAS}/{extended['id']}/aditivos",
        json={"kind": "prazo", "nova_vigencia_fim": "2027-07-01", "justification": "Prorrogada."},
        headers=gestor,
    )
    only_value = make(application, gestor, activate=True, vigencia_fim="2026-07-10")
    application.post(
        f"{ATAS}/{only_value['id']}/aditivos",
        json={"kind": "valor", "valor_acrescimo": "1000.00", "justification": "Mais verba."},
        headers=gestor,
    )
    servidor = _login(application, create_user, "servidor")

    response = application.get(f"{ATAS}/alertas/renovacao", headers=servidor)

    assert response.status_code == 200
    mine = {late["id"], soon["id"], far["id"], draft["id"], extended["id"], only_value["id"]}
    listed = [row for row in response.json() if row["ata"]["id"] in mine]
    assert [row["ata"]["id"] for row in listed] == [soon["id"], only_value["id"], late["id"]]
    assert [row["days_remaining"] for row in listed] == [19, 39, 75]


# ── AC-0002-13, -14 — aditivos ──────────────────────────────────────────────


def test_ac_0002_13_an_aditivo_of_value_raises_valor_contratado(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0002-13 — its own record, with its justification, and an audit row."""
    ata = make(application, gestor, activate=True)

    response = application.post(
        f"{ATAS}/{ata['id']}/aditivos",
        json={"kind": "valor", "valor_acrescimo": "5000.50", "justification": "Mais demanda."},
        headers=gestor,
    )

    assert response.status_code == 201, response.text
    detail = response.json()
    assert decimal.Decimal(detail["valor_contratado"]) == decimal.Decimal("105000.50")
    assert decimal.Decimal(detail["total_value"]) == decimal.Decimal("100000.00")
    assert [(a["kind"], a["justification"]) for a in detail["aditivos"]] == [
        ("valor", "Mais demanda.")
    ]
    row = audit_rows(db_session, ata["id"], "ata.aditivo_registrado")[0]
    assert row.justificativa == "Mais demanda."
    assert row.dados_anteriores == {"valor_contratado": "100000.00"}


def test_ac_0002_13_an_aditivo_of_prazo_sets_the_new_vigencia_fim(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0002-13 — the end moves; the audit row keeps the old one."""
    ata = make(application, gestor, activate=True)

    response = application.post(
        f"{ATAS}/{ata['id']}/aditivos",
        json={"kind": "prazo", "nova_vigencia_fim": "2027-03-31", "justification": "Prorrogação."},
        headers=gestor,
    )

    assert response.status_code == 201
    assert response.json()["vigencia_fim"] == "2027-03-31"
    row = audit_rows(db_session, ata["id"], "ata.aditivo_registrado")[0]
    assert row.dados_anteriores == {"vigencia_fim": "2026-12-31"}


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "valor", "valor_acrescimo": "100.00"},
        {"kind": "valor", "valor_acrescimo": "100.00", "justification": ""},
        {"kind": "valor", "valor_acrescimo": "0", "justification": "x"},
        {"kind": "valor", "justification": "x"},
        {"kind": "prazo", "justification": "x"},
        {"kind": "prazo", "nova_vigencia_fim": "2026-06-01", "justification": "x"},
    ],
)
def test_ac_0002_13_an_incomplete_aditivo_is_refused(
    application: TestClient, gestor: dict[str, str], db_session: Session, payload: dict
) -> None:
    """AC-0002-13 — no justification, no figure, or a date that does not extend: 422."""
    ata = make(application, gestor, activate=True)

    response = application.post(f"{ATAS}/{ata['id']}/aditivos", json=payload, headers=gestor)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "INVALID_DATA"
    assert application.get(f"{ATAS}/{ata['id']}", headers=gestor).json()["aditivos"] == []


@pytest.mark.parametrize("move", [None, "suspender", "encerrar"])
def test_ac_0002_13_an_aditivo_needs_a_vigente_ata(
    application: TestClient, gestor: dict[str, str], move: str | None
) -> None:
    """AC-0002-13 — a draft, suspended or closed ATA answers 409 `ATA_NAO_VIGENTE`."""
    ata = make(application, gestor, activate=move is not None)
    if move:
        application.post(f"{ATAS}/{ata['id']}/{move}", headers=gestor)

    response = application.post(
        f"{ATAS}/{ata['id']}/aditivos",
        json={"kind": "valor", "valor_acrescimo": "10.00", "justification": "x"},
        headers=gestor,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ATA_NAO_VIGENTE"


def test_ac_0002_14_the_aditivos_of_value_stop_at_a_quarter(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0002-14 — 20.000 plus 6.000 on 100.000 is refused; exactly 25.000 is the ceiling."""
    ata = make(application, gestor, activate=True)

    def aditivo(value: str) -> object:
        return application.post(
            f"{ATAS}/{ata['id']}/aditivos",
            json={"kind": "valor", "valor_acrescimo": value, "justification": "Mais verba."},
            headers=gestor,
        )

    assert aditivo("20000.00").status_code == 201
    over = aditivo("6000.00")
    assert over.status_code == 422
    assert over.json()["error"]["code"] == "ADITIVO_ACIMA_DO_LIMITE"
    detail = application.get(f"{ATAS}/{ata['id']}", headers=gestor).json()
    assert len(detail["aditivos"]) == 1
    assert aditivo("5000.00").status_code == 201
    assert aditivo("0.01").status_code == 422


# ── AC-0002-08, -19, -21 — reajuste requests ────────────────────────────────


def test_ac_0002_19_a_gestor_records_a_reajuste_request(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """AC-0002-19 — stored against the ATA, and audited with the gestor as actor."""
    ata = make(application, gestor, activate=True)

    response = application.post(
        f"{ATAS}/{ata['id']}/reajustes",
        json={"processo_sei": PROCESSO, "requested_on": "2027-02-01"},
        headers=gestor,
    )

    assert response.status_code == 201, response.text
    assert [(r["processo_sei"], r["requested_on"]) for r in response.json()["reajustes"]] == [
        (PROCESSO, "2027-02-01")
    ]
    rows = audit_rows(db_session, ata["id"], "ata.reajuste_registrado")
    assert len(rows) == 1 and rows[0].usuario_id is not None


@pytest.mark.parametrize("bad", ["12345", "12345.12345/2026-12", "abcde.123456/2026-12", ""])
def test_ac_0002_19_a_malformed_processo_sei_is_refused(
    application: TestClient, gestor: dict[str, str], bad: str
) -> None:
    """AC-0002-19 — 422 `PROCESSO_SEI_INVALIDO`, the message stating the format."""
    ata = make(application, gestor, activate=True)

    response = application.post(
        f"{ATAS}/{ata['id']}/reajustes",
        json={"processo_sei": bad or "x", "requested_on": "2027-02-01"},
        headers=gestor,
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "PROCESSO_SEI_INVALIDO"
    assert "NNNNN.NNNNNN/AAAA-DD" in response.json()["error"]["message"]


def test_ac_0002_19_a_request_needs_a_vigente_ata(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0002-19 — a draft ATA answers 409 `ATA_NAO_VIGENTE`."""
    ata = make(application, gestor)

    response = application.post(
        f"{ATAS}/{ata['id']}/reajustes",
        json={"processo_sei": PROCESSO, "requested_on": "2027-02-01"},
        headers=gestor,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ATA_NAO_VIGENTE"


def test_ac_0002_08_the_processo_sei_is_checked_by_format_and_nothing_else(
    application: TestClient, gestor: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-0002-08 — no name is resolved and no connection is opened to an external system."""
    ata = make(application, gestor, activate=True)
    lookups: list[object] = []
    real = socket.getaddrinfo

    def watch(host, *args, **kwargs):  # type: ignore[no-untyped-def]
        lookups.append(host)
        return real(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", watch)

    response = application.post(
        f"{ATAS}/{ata['id']}/reajustes",
        json={"processo_sei": PROCESSO, "requested_on": "2027-02-01"},
        headers=gestor,
    )

    assert response.status_code == 201
    assert lookups == []


# ── AC-0002-18, -20, -21 — the reajuste date and its alert ──────────────────


@pytest.mark.parametrize(
    "budget,expected",
    [("2026-03-10", "2027-03-10"), ("2028-02-29", "2029-02-28"), ("2027-12-31", "2028-12-31")],
)
def test_ac_0002_18_the_reajuste_date_is_one_year_after_the_orcamento(
    application: TestClient,
    gestor: dict[str, str],
    db_session: Session,
    budget: str,
    expected: str,
) -> None:
    """AC-0002-18 — derived, and a 29/02 falls due on 28/02."""
    ata = make(application, gestor, budget_date=budget)

    assert ata["data_reajuste"] == expected
    db_session.rollback()
    columns = {
        r[0]
        for r in db_session.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'ata'")
        )
    }
    assert "data_reajuste" not in columns


def test_ac_0002_20_the_reajuste_alert(
    application: TestClient, gestor: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-0002-20 — within the window or past, soonest first, gone once a request exists."""
    freeze(monkeypatch, "2026-06-01")
    past = make(application, gestor, activate=True, budget_date="2025-05-20")  # due 2026-05-20
    soon = make(application, gestor, activate=True, budget_date="2025-06-15")  # due 2026-06-15
    later = make(application, gestor, activate=True, budget_date="2025-08-01")  # due 2026-08-01
    far = make(application, gestor, activate=True, budget_date="2026-03-01")  # due 2027-03-01
    draft = make(application, gestor, budget_date="2025-06-10")
    mine = {past["id"], soon["id"], later["id"], far["id"], draft["id"]}

    def listed() -> list[dict]:
        rows = application.get(f"{ATAS}/alertas/reajuste", headers=gestor).json()
        return [r for r in rows if r["ata"]["id"] in mine]

    first = listed()
    assert [r["ata"]["id"] for r in first] == [past["id"], soon["id"], later["id"]]
    assert [r["days_remaining"] for r in first] == [-12, 14, 61]

    done = application.post(
        f"{ATAS}/{soon['id']}/reajustes",
        json={"processo_sei": PROCESSO, "requested_on": "2026-06-01"},
        headers=gestor,
    )
    assert done.status_code == 201
    assert [r["ata"]["id"] for r in listed()] == [past["id"], later["id"]]


def test_ac_0002_20_the_alert_follows_the_clock(
    application: TestClient, gestor: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-0002-20 — the same ATA at three dates, with no write between them."""
    ata = make(application, gestor, activate=True, budget_date="2025-09-01")  # due 2026-09-01

    def present(day: str) -> bool:
        freeze(monkeypatch, day)
        rows = application.get(f"{ATAS}/alertas/reajuste", headers=gestor).json()
        return any(r["ata"]["id"] == ata["id"] for r in rows)

    assert [present("2026-05-01"), present("2026-06-15"), present("2026-10-01")] == [
        False,
        True,
        True,
    ]


def test_ac_0002_21_recording_a_request_changes_no_price(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """AC-0002-21 — the ATA's figures are the same after the request.

    The criterion speaks of an `ITEM_ATA`, which SPEC-0003 owns; until it exists
    the figures a reajuste could touch are the ATA's own.
    """
    ata = make(application, gestor, activate=True)

    application.post(
        f"{ATAS}/{ata['id']}/reajustes",
        json={"processo_sei": PROCESSO, "requested_on": "2027-02-01"},
        headers=gestor,
    )

    after = application.get(f"{ATAS}/{ata['id']}", headers=gestor).json()
    assert after["total_value"] == ata["total_value"]
    assert after["valor_contratado"] == ata["valor_contratado"]


# ── AC-0002-16 — audited in the same transaction ────────────────────────────


def test_ac_0002_16_a_mutation_whose_audit_row_fails_is_not_saved(
    create_user: Callable[..., User], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-0002-16 — if the history cannot be written, the ATA does not exist."""
    from app.services import atas

    actor = create_user(perfil="gestor")
    number = f"ATA-{uuid.uuid4().hex[:10]}"

    def broken(*args: object, **kwargs: object) -> None:
        raise RuntimeError("audit down")

    monkeypatch.setattr(atas, "record", broken)
    with pytest.raises(RuntimeError):
        atas.register(
            db_session,
            actor=db_session.get(User, actor.id),  # type: ignore[arg-type]
            number=number,
            subject="Objeto",
            organ="Órgão",
            fornecedor=atas.FornecedorInput(cnpj=CNPJ, legal_name="Empresa"),
            issued_on=None,
            vigencia_inicio=datetime.date(2026, 1, 1),
            vigencia_fim=datetime.date(2026, 12, 31),
            total_value=decimal.Decimal("10.00"),
            budget_date=datetime.date(2026, 3, 1),
            at=datetime.datetime.now(datetime.UTC),
            correlation_id=uuid.uuid4(),
        )
    db_session.rollback()

    count = db_session.execute(
        text("SELECT count(*) FROM ata WHERE numero = :n"), {"n": number}
    ).scalar_one()
    assert count == 0
