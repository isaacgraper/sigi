"""The ATA notices and the bell — SPEC-0008 v1.1, AC-0008-01 to -05.

The daily check raises a notice once per ATA and reason, and every perfil reads
the same ones. The e-mail summary is `test_resumo.py`'s. The database is shared
by the suite, so each test looks at its own ATAs.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.models.audit_log import AuditLog
from app.models.notificacao import Notificacao
from app.models.user import User
from app.services import notificacoes as service
from tests.catalogue import login, make_ata
from tests.test_notas_empenho import open_ne, setup_ata, to_stage
from tests.test_notas_fiscais import error

AVISOS = "/api/v1/notificacoes"
ATAS = "/api/v1/atas"


@pytest.fixture
def gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in gestor."""
    return login(application, create_user, "gestor")[0]


def day(days: int) -> str:
    """A date `days` from today in São Paulo, as the API reads it."""
    return (clock.local_date(clock.now()) + datetime.timedelta(days=days)).isoformat()


def check(db_session: Session) -> None:
    """Run the daily check as the scheduled command does, and keep what it raised."""
    service.check(db_session, at=clock.now(), correlation_id=uuid.uuid4())
    db_session.commit()


def notices_of(db_session: Session, ata_id: str) -> list[Notificacao]:
    """The notices of one ATA, oldest first."""
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(Notificacao)
            .where(Notificacao.ata_id == uuid.UUID(ata_id))
            .order_by(Notificacao.criada_em)
        )
    )


def reasons(db_session: Session, ata_id: str) -> list[str]:
    """The reasons raised for one ATA."""
    return sorted(notice.motivo for notice in notices_of(db_session, ata_id))


def issued_share(application: TestClient, gestor: dict[str, str], quantity: str) -> dict:
    """An ATA of 10.000,00 in one item of 1.000 at 10, with an NE of `quantity` issued."""
    ata, items = setup_ata(application, gestor, [("1000", "10")], total="10000.00")
    created = open_ne(application, gestor, ata["id"], [(items[0]["id"], quantity)])
    assert created.status_code == 201, created.text
    to_stage(application, gestor, created.json()["id"], "ne_emitida")
    return ata


# ── AC-0008-01 — the reasons ────────────────────────────────────────────────


def test_AC_0008_01_RF19_an_ata_about_to_end_will_vencer(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """Within 90 days of its end, with no aditivo de prazo."""
    soon = make_ata(application, gestor, vigencia_fim=day(30))
    far = make_ata(application, gestor, vigencia_fim=day(200))

    check(db_session)

    assert reasons(db_session, soon["id"]) == ["vai_vencer"]
    assert reasons(db_session, far["id"]) == []


def test_AC_0008_01_an_ata_past_its_end_venceu(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """A vigente ATA whose vigência has ended."""
    ata = make_ata(application, gestor, vigencia_inicio="2025-01-01", vigencia_fim=day(-3))

    check(db_session)

    assert "venceu" in reasons(db_session, ata["id"])
    assert "vai_vencer" not in reasons(db_session, ata["id"])


def test_AC_0008_01_an_ata_at_80_percent_and_one_esgotada(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """The alto consumo of SPEC-0006, and a saldo disponível of zero."""
    high = issued_share(application, gestor, "850")
    empty = issued_share(application, gestor, "1000")

    check(db_session)

    assert reasons(db_session, high["id"]) == ["saldo_80"]
    assert notices_of(db_session, high["id"])[0].dados == {"comprometimento_percentual": "85.00"}
    assert reasons(db_session, empty["id"]) == ["saldo_esgotado"]


def test_AC_0008_01_an_ata_whose_reajuste_is_due(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """The reajuste of AC-0002-20, with no request."""
    ata = make_ata(application, gestor, vigencia_inicio="2025-01-01", budget_date=day(-400))

    check(db_session)

    assert "reajuste" in reasons(db_session, ata["id"])


# ── AC-0008-02 — once per ATA and reason ────────────────────────────────────


def test_AC_0008_02_a_reason_that_still_holds_is_not_raised_twice(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """The second run finds the notice already there."""
    ata = make_ata(application, gestor, vigencia_fim=day(30))

    check(db_session)
    check(db_session)

    assert reasons(db_session, ata["id"]) == ["vai_vencer"]


def test_AC_0008_02_an_aditivo_lets_the_reason_be_raised_again(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """A new valor contratado is a new key for the saldo's reason."""
    ata = issued_share(application, gestor, "900")
    check(db_session)
    aditivo = application.post(
        f"{ATAS}/{ata['id']}/aditivos",
        json={"kind": "valor", "valor_acrescimo": "500.00", "justification": "Mais demanda."},
        headers=gestor,
    )
    assert aditivo.status_code == 201, aditivo.text

    check(db_session)

    assert [n.chave for n in notices_of(db_session, ata["id"])] == ["10000.00", "10500.00"]


# ── AC-0008-03 to -05 — the bell, the same for everyone ─────────────────────


def bell(application: TestClient, headers: dict[str, str]) -> dict:
    """The notices as one member reads them; they must be served."""
    response = application.get(AVISOS, params={"size": 100}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def mine(page: dict, ata_id: str) -> list[dict]:
    """The notices of one ATA on a page."""
    return [item for item in page["items"] if item["ata_id"] == ata_id]


def test_AC_0008_03_AC_0008_04_every_perfil_reads_the_same_notices(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    db_session: Session,
) -> None:
    """Gestor, servidor and auditor, the same notice, with its ATA and its reason."""
    ata = make_ata(application, gestor, vigencia_fim=day(30))
    check(db_session)
    servidor = login(application, create_user, "servidor")[0]
    auditor = login(application, create_user, "auditor")[0]

    seen = [mine(bell(application, headers), ata["id"]) for headers in (gestor, servidor, auditor)]

    assert seen[0] == seen[1] == seen[2]
    notice = seen[0][0]
    assert (notice["ata_number"], notice["motivo"], notice["motivo_rotulo"]) == (
        ata["number"],
        "vai_vencer",
        "Vai vencer",
    )
    assert notice["lida"] is False


def test_AC_0008_05_reading_is_one_member_s_own(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    db_session: Session,
) -> None:
    """One member reads a notice; another still has it unread."""
    ata = make_ata(application, gestor, vigencia_fim=day(30))
    check(db_session)
    other = login(application, create_user, "servidor")[0]
    notice_id = mine(bell(application, gestor), ata["id"])[0]["id"]
    before = bell(application, gestor)["nao_lidas"]

    read = application.post(f"{AVISOS}/{notice_id}/lida", headers=gestor)

    assert read.status_code == 204
    assert mine(bell(application, gestor), ata["id"])[0]["lida"] is True
    assert bell(application, gestor)["nao_lidas"] == before - 1
    assert mine(bell(application, other), ata["id"])[0]["lida"] is False


def test_AC_0008_05_marking_all_read(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """Every notice read at once, and the count at zero."""
    make_ata(application, gestor, vigencia_fim=day(30))
    check(db_session)

    response = application.post(f"{AVISOS}/lidas", headers=gestor)

    assert response.status_code == 204
    page = bell(application, gestor)
    assert page["nao_lidas"] == 0
    assert all(item["lida"] for item in page["items"])


def test_AC_0008_05_an_unknown_notice_is_not_found(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """Marking a notice that does not exist."""
    response = application.post(f"{AVISOS}/{uuid.uuid4()}/lida", headers=gestor)

    assert response.status_code == 404
    assert error(response)["code"] == "NOT_FOUND"


# ── The history of the check ────────────────────────────────────────────────


def test_AC_0008_01_the_check_records_each_notice(
    application: TestClient, gestor: dict[str, str], db_session: Session
) -> None:
    """A notice raised writes its history row."""
    ata = make_ata(application, gestor, vigencia_fim=day(30))

    check(db_session)

    notice = notices_of(db_session, ata["id"])[0]
    row = db_session.scalars(select(AuditLog).where(AuditLog.entidade_id == notice.id)).one()
    assert row.acao == "notificacao.criada"
    assert row.dados_anteriores == {"ata_id": ata["id"], "motivo": "vai_vencer", "chave": day(30)}
