"""Saldo of an ATA in value and per item in quantity — SPEC-0006 v1.0.

AC-0006-05 is carried by SPEC-0004 AC-0004-16. AC-0006-14 and -15 need the NFs
of SPEC-0005 and have no test yet.
"""

from __future__ import annotations

import datetime
import decimal
import statistics
import time
import uuid
from collections.abc import Callable

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.models.user import User
from tests.catalogue import ATAS, login
from tests.test_notas_empenho import (
    item_saldo,
    money,
    open_ne,
    saldo,
    setup_ata,
    to_stage,
)


@pytest.fixture
def gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    """Headers for a signed-in gestor."""
    return login(application, create_user, "gestor")[0]


def test_ac_0006_01_no_nes(application: TestClient, gestor: dict) -> None:
    """AC-0006-01 — with no NE, saldo is the contracted value and nothing is committed."""
    ata, _ = setup_ata(application, gestor, [("10", "10")], total="100000.00")

    s = saldo(application, gestor, ata["id"])

    assert money(s["saldo_disponivel"]) == decimal.Decimal("100000.00")
    assert money(s["comprometimento_percentual"]) == 0
    assert s["alto_consumo"] is False


@pytest.mark.parametrize("split", [1, 4])
def test_ac_0006_02_tela_5_example(application: TestClient, gestor: dict, split: int) -> None:
    """AC-0006-02 — R$ 78.000,00 issued on R$ 2.840.000,00, in one item or four: 3%."""
    lines = [("1000", str(decimal.Decimal("78000") / split / 100))] * split
    ata, items = setup_ata(application, gestor, lines, total="2840000.00")
    ne_id = open_ne(application, gestor, ata["id"], [(i["id"], "100") for i in items]).json()["id"]
    to_stage(application, gestor, ne_id, "ne_emitida")

    s = saldo(application, gestor, ata["id"])

    assert money(s["saldo_disponivel"]) == decimal.Decimal("2762000.00")
    assert money(s["valor_reservado"]) == 0
    assert money(s["valor_empenhado"]) == decimal.Decimal("78000.00")
    assert round(money(s["comprometimento_percentual"])) == 3


@pytest.mark.parametrize(
    ("committed", "flag"), [("79900.00", False), ("80000.00", True), ("80100.00", True)]
)
def test_ac_0006_03_alto_consumo_boundary(
    application: TestClient, gestor: dict, committed: str, flag: bool
) -> None:
    """AC-0006-03 — 79,9% is not flagged; 80,0% and 80,1% are."""
    ata, items = setup_ata(application, gestor, [("1", committed)], total="100000.00")
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")]).json()["id"]
    to_stage(application, gestor, ne_id, "pre_empenho")

    assert saldo(application, gestor, ata["id"])["alto_consumo"] is flag


def test_ac_0006_04_aditivo_lowers_commitment(application: TestClient, gestor: dict) -> None:
    """AC-0006-04 — R$ 50.000,00 of R$ 100.000,00, then an aditivo of R$ 25.000,00: 40%."""
    ata, items = setup_ata(application, gestor, [("1", "50000")], total="100000.00")
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "1")]).json()["id"]
    to_stage(application, gestor, ne_id, "ne_emitida")

    response = application.post(
        f"{ATAS}/{ata['id']}/aditivos",
        json={"kind": "valor", "valor_acrescimo": "25000.00", "justification": "Acréscimo."},
        headers=gestor,
    )

    assert response.status_code == 201, response.text
    s = saldo(application, gestor, ata["id"])
    assert money(s["valor_contratado"]) == decimal.Decimal("125000.00")
    assert money(s["comprometimento_percentual"]) == 40


def test_ac_0006_06_derived_on_every_read(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """AC-0006-06 — a line changed in the database shows on the next read, no refresh step."""
    ata, items = setup_ata(application, gestor, [("100", "100")], total="100000.00")
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "10")]).json()["id"]
    to_stage(application, gestor, ne_id, "pre_empenho")
    assert money(saldo(application, gestor, ata["id"])["valor_reservado"]) == 1000

    admin_connection.execute(
        "UPDATE item_nota_empenho SET quantidade = 20, valor = 2000 WHERE nota_empenho_id = %s",
        (ne_id,),
    )

    assert money(saldo(application, gestor, ata["id"])["valor_reservado"]) == 2000


def test_ac_0006_07_p95_under_300ms(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """AC-0006-07 — 500 ATAs and 10.000 NEs of three lines; one ATA's saldo under 300 ms p95."""
    ata, items = setup_ata(application, gestor, [("1000000", "1")] * 3, total="1000000.00")
    owner = admin_connection.execute("SELECT responsavel_id FROM ata WHERE id = %s", (ata["id"],))
    owner_id = owner.fetchone()[0]  # type: ignore[index]
    batch = uuid.uuid4().hex[:6].upper()
    admin_connection.execute(
        """
        WITH atas AS (
          INSERT INTO ata (numero, objeto, orgao, fornecedor_id, vigencia_inicio, vigencia_fim,
                           valor_total, data_orcamento_planilhado, responsavel_id)
          SELECT 'PERF-' || %(b)s || '-' || g, 'Carga', 'Órgão', a.fornecedor_id,
                 a.vigencia_inicio, a.vigencia_fim, 1000000, a.data_orcamento_planilhado, %(o)s
          FROM generate_series(1, 499) g, (SELECT * FROM ata WHERE id = %(a)s) a
          RETURNING id
        ), nes AS (
          INSERT INTO nota_empenho (processo_sei, ata_id, responsavel_id, status)
          SELECT '00301.000451/2026-12', %(a)s, %(o)s, 'demanda'
          FROM generate_series(1, 10000)
          RETURNING id
        )
        INSERT INTO item_nota_empenho (nota_empenho_id, item_ata_id, quantidade, valor_unitario,
                                       valor)
        SELECT nes.id, i.id, 1, 1, 1 FROM nes, item_ata i WHERE i.ata_id = %(a)s
        """,
        {"a": ata["id"], "o": owner_id, "b": batch},
    )
    admin_connection.execute(
        "UPDATE nota_empenho SET status = 'pre_empenho', numero_pre_empenho = 'P' || "
        "substr(replace(id::text, '-', ''), 1, 19) WHERE ata_id = %s AND status = 'demanda'",
        (ata["id"],),
    )
    admin_connection.execute("ANALYZE nota_empenho; ANALYZE item_nota_empenho")

    timings = []
    for _ in range(20):
        start = time.perf_counter()
        s = saldo(application, gestor, ata["id"])
        timings.append(time.perf_counter() - start)

    assert money(s["valor_reservado"]) == 30000
    assert statistics.quantiles(timings, n=20)[18] < 0.3


def test_ac_0006_08_money_is_exact(
    application: TestClient, gestor: dict, admin_connection: psycopg.Connection
) -> None:
    """AC-0006-08 — 1.000 NEs of R$ 0,01 issued sum to exactly R$ 10,00."""
    ata, items = setup_ata(application, gestor, [("1000", "0.01")], total="100.00")
    owner_id = admin_connection.execute(
        "SELECT responsavel_id FROM ata WHERE id = %s", (ata["id"],)
    ).fetchone()[0]  # type: ignore[index]
    admin_connection.execute(
        """
        WITH nes AS (
          INSERT INTO nota_empenho (processo_sei, ata_id, responsavel_id, status)
          SELECT '00301.000451/2026-12', %(a)s, %(o)s, 'demanda' FROM generate_series(1, 1000)
          RETURNING id
        )
        INSERT INTO item_nota_empenho (nota_empenho_id, item_ata_id, quantidade, valor_unitario,
                                       valor)
        SELECT nes.id, %(i)s, 1, 0.01, 0.01 FROM nes
        """,
        {"a": ata["id"], "o": owner_id, "i": items[0]["id"]},
    )
    admin_connection.execute(
        "UPDATE nota_empenho SET status = 'ne_emitida', data_emissao = current_date,"
        " numero_pre_empenho = 'P' || substr(replace(id::text, '-', ''), 1, 19),"
        " numero = 'N' || substr(replace(id::text, '-', ''), 1, 19) WHERE ata_id = %s",
        (ata["id"],),
    )

    assert money(saldo(application, gestor, ata["id"])["valor_empenhado"]) == decimal.Decimal(
        "10.00"
    )


def test_ac_0006_09_calculado_em(application: TestClient, gestor: dict) -> None:
    """AC-0006-09 — the response states the instant it was summed."""
    ata, _ = setup_ata(application, gestor, [("10", "10")])

    stated = datetime.datetime.fromisoformat(saldo(application, gestor, ata["id"])["calculado_em"])

    assert abs((datetime.datetime.now(datetime.UTC) - stated).total_seconds()) < 60


def test_ac_0006_10_quantity_per_item(application: TestClient, gestor: dict) -> None:
    """AC-0006-10 — 20 contracted, 5 issued and 3 reserved leave 12."""
    ata, items = setup_ata(application, gestor, [("20", "1200")], total="500000.00")
    first = open_ne(application, gestor, ata["id"], [(items[0]["id"], "5")]).json()["id"]
    to_stage(application, gestor, first, "ne_emitida")
    second = open_ne(application, gestor, ata["id"], [(items[0]["id"], "3")]).json()["id"]
    to_stage(application, gestor, second, "pre_empenho")

    item = item_saldo(application, gestor, ata["id"], items[0]["id"])

    assert money(item["quantidade_disponivel"]) == 12
    assert money(saldo(application, gestor, ata["id"])["saldo_disponivel"]) == decimal.Decimal(
        "490400.00"
    )


def test_ac_0006_11_value_and_quantity_disagree(application: TestClient, gestor: dict) -> None:
    """AC-0006-11 — budget left on the ATA, the item esgotado."""
    ata, items = setup_ata(application, gestor, [("3", "100")], total="500000.00")
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "3")]).json()["id"]
    to_stage(application, gestor, ne_id, "pre_empenho")

    assert money(saldo(application, gestor, ata["id"])["saldo_disponivel"]) > 0
    assert item_saldo(application, gestor, ata["id"], items[0]["id"])["esgotado"] is True


def test_ac_0006_12_rn15_aditivo_raises_the_ceiling(application: TestClient, gestor: dict) -> None:
    """AC-0006-12 — 100 contracted, 100 committed, an aditivo of 25%: 25 available."""
    ata, items = setup_ata(application, gestor, [("100", "10")], total="100000.00")
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "100")]).json()["id"]
    to_stage(application, gestor, ne_id, "ne_emitida")

    response = application.post(
        f"{ATAS}/{ata['id']}/aditivos",
        json={
            "kind": "quantidade",
            "item_id": items[0]["id"],
            "quantity": "25",
            "justification": "Acréscimo de quantitativo.",
        },
        headers=gestor,
    )

    assert response.status_code == 201, response.text
    item = item_saldo(application, gestor, ata["id"], items[0]["id"])
    assert money(item["quantidade_disponivel"]) == 25


def test_ac_0006_13_rn17_reserved_then_committed(application: TestClient, gestor: dict) -> None:
    """AC-0006-13 — 300 of 1.000: 700 with 300 reserved, then 700 with 300 committed."""
    ata, items = setup_ata(application, gestor, [("1000", "1")], total="100000.00")
    ne_id = open_ne(application, gestor, ata["id"], [(items[0]["id"], "300")]).json()["id"]
    to_stage(application, gestor, ne_id, "pre_empenho")

    reserved = item_saldo(application, gestor, ata["id"], items[0]["id"])
    assert money(reserved["quantidade_disponivel"]) == 700
    assert money(reserved["quantidade_reservada"]) == 300
    before = saldo(application, gestor, ata["id"])["saldo_disponivel"]

    to_stage(application, gestor, ne_id, "ne_emitida")

    issued = item_saldo(application, gestor, ata["id"], items[0]["id"])
    assert money(issued["quantidade_disponivel"]) == 700
    assert money(issued["quantidade_reservada"]) == 0
    assert money(issued["quantidade_empenhada"]) == 300
    assert saldo(application, gestor, ata["id"])["saldo_disponivel"] == before


def test_ac_0006_16_unknown_ata(application: TestClient, gestor: dict) -> None:
    """AC-0006-16 — an unknown ATA is 404 on both reads."""
    for path in ("saldo", "itens/saldo"):
        response = application.get(f"{ATAS}/{uuid.uuid4()}/{path}", headers=gestor)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
