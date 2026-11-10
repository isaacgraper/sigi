"""Reading the audit trail — SPEC-0007 v1.0.

The history is read by the gestor and the auditor only (AC-0007-08, -09); the
cycle of an insumo is read by every perfil, inside the RN07 scope (AC-0007-07).
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.core import clock
from app.models.user import User
from tests.catalogue import grupo, login
from tests.test_insumos import scoped_servidor
from tests.test_notas_empenho import open_ne, setup_ata, to_stage
from tests.test_notas_fiscais import error, launched

HIST = "/api/v1/historico"
INSUMOS = "/api/v1/insumos"
RANK = {"ata": 0, "item_ata": 1, "nota_empenho": 2, "nota_fiscal": 3}


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
    """An ATA of two items, an NE issued on the first and an NF launched against it."""
    ata, items = setup_ata(application, gestor, [("1000", "10"), ("500", "2")])
    created = open_ne(application, gestor, ata["id"], [(items[0]["id"], "300")])
    assert created.status_code == 201, created.text
    ne = to_stage(application, gestor, created.json()["id"], "ne_emitida")
    nf = launched(application, gestor, ne, "100", "1000.00")
    return ata, items, ne, nf


def read_cycle(application: TestClient, headers: dict[str, str], insumo_id: str) -> dict:
    """The cycle of an insumo; it must be served."""
    response = application.get(f"{INSUMOS}/{insumo_id}/ciclo", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def history(application: TestClient, headers: dict[str, str], **params: str | int) -> dict:
    """A page of the history; it must be served."""
    response = application.get(HIST, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def today() -> datetime.date:
    """Today in São Paulo, the day the rows written now fall on."""
    return clock.local_date(clock.now())


# ── AC-0007-07 ─ the cycle of an insumo ──────────────────────────────────────


def test_AC_0007_07_RF06_the_cycle_reads_ata_to_nf_in_order(
    application: TestClient,
    gestor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """The cycle reads ATA, item, NE and NF, oldest first."""
    ata, items, ne, nf = cycle
    insumo_id = items[0]["insumo"]["id"]

    body = read_cycle(application, gestor, insumo_id)

    assert body["insumo_id"] == insumo_id
    etapas = [e["etapa"] for e in body["eventos"]]
    assert set(etapas) == set(RANK)
    assert etapas == sorted(etapas, key=RANK.__getitem__)
    by_etapa = {e["entidade_id"] for e in body["eventos"] if e["etapa"] in ("ata", "item_ata")}
    assert by_etapa == {ata["id"]}
    assert {e["entidade_id"] for e in body["eventos"] if e["etapa"] == "nota_empenho"} == {ne["id"]}
    assert {e["entidade_id"] for e in body["eventos"] if e["etapa"] == "nota_fiscal"} == {nf["id"]}
    moments = [e["ocorrido_em"] for e in body["eventos"]]
    assert moments == sorted(moments)
    assert len([e for e in body["eventos"] if e["etapa"] == "nota_empenho"]) >= 5


def test_AC_0007_07_the_other_items_of_the_ata_stay_out(
    application: TestClient,
    gestor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """An insumo's cycle carries only its own item of the ATA."""
    _, items, _, _ = cycle

    first = read_cycle(application, gestor, items[0]["insumo"]["id"])
    second = read_cycle(application, gestor, items[1]["insumo"]["id"])

    def item_ids(body: dict) -> set[str]:
        return {
            e["dados_anteriores"]["item_ata_id"]
            for e in body["eventos"]
            if e["etapa"] == "item_ata"
        }

    assert item_ids(first) == {items[0]["id"]}
    assert item_ids(second) == {items[1]["id"]}
    assert {e["etapa"] for e in second["eventos"]} == {"ata", "item_ata"}


def test_AC_0007_07_every_perfil_reads_the_cycle(
    application: TestClient,
    gestor: dict[str, str],
    auditor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """The auditor reads the cycle too."""
    _, items, _, _ = cycle

    assert read_cycle(application, auditor, items[0]["insumo"]["id"])["eventos"]


def test_AC_0007_07_an_unknown_insumo_is_not_found(
    application: TestClient, gestor: dict[str, str]
) -> None:
    """An insumo that does not exist has no cycle."""
    response = application.get(f"{INSUMOS}/{uuid.uuid4()}/ciclo", headers=gestor)

    assert response.status_code == 404
    assert error(response)["code"] == "NOT_FOUND"


def test_AC_0007_07_RN07_outside_the_grupo_the_insumo_does_not_exist(
    application: TestClient,
    create_user: Callable[..., User],
    gestor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """A servidor of another grupo is told the insumo does not exist."""
    _, items, _, _ = cycle
    elsewhere = scoped_servidor(application, create_user, gestor, grupo(application, gestor)["id"])

    response = application.get(f"{INSUMOS}/{items[0]['insumo']['id']}/ciclo", headers=elsewhere)

    assert response.status_code == 404
    assert error(response)["code"] == "NOT_FOUND"


# ── AC-0007-08 ─ querying the history ────────────────────────────────────────


def test_AC_0007_08_RF10_by_entity_newest_first(
    application: TestClient,
    gestor: dict[str, str],
    auditor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """The rows of one NE, newest first, ending at its creation."""
    _, _, ne, _ = cycle

    body = history(application, auditor, entidade_tipo="nota_empenho", entidade_id=ne["id"])

    assert body["total"] >= 5
    assert {row["entidade_id"] for row in body["items"]} == {ne["id"]}
    moments = [row["ocorrido_em"] for row in body["items"]]
    assert moments == sorted(moments, reverse=True)
    assert body["items"][-1]["acao"] == "ne.criada"


def test_AC_0007_08_by_usuario(
    application: TestClient,
    gestor_user: tuple[dict, User],
    auditor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """Filtered by usuario, only that usuario's rows are served."""
    _, user = gestor_user

    body = history(application, auditor, usuario_id=str(user.id), size=100)

    assert body["total"] > 0
    assert {row["usuario_id"] for row in body["items"]} == {str(user.id)}


def test_AC_0007_08_a_page_at_a_time(
    application: TestClient,
    gestor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """The second page is the slice of the whole list it names."""
    _, _, ne, _ = cycle
    whole = history(application, gestor, entidade_tipo="nota_empenho", entidade_id=ne["id"])

    second = history(
        application, gestor, entidade_tipo="nota_empenho", entidade_id=ne["id"], page=2, size=2
    )

    assert second["total"] == whole["total"]
    assert (second["page"], second["size"]) == (2, 2)
    assert [r["id"] for r in second["items"]] == [r["id"] for r in whole["items"][2:4]]


def test_AC_0007_08_a_period_is_whole_local_days(
    application: TestClient,
    gestor: dict[str, str],
    cycle: tuple[dict, list[dict], dict, dict],
) -> None:
    """A period covers whole days in São Paulo, `ate` included."""
    _, _, ne, _ = cycle
    day = today()
    keys = {"entidade_tipo": "nota_empenho", "entidade_id": ne["id"]}

    inside = history(application, gestor, de=day.isoformat(), ate=day.isoformat(), **keys)
    before = history(
        application, gestor, ate=(day - datetime.timedelta(days=1)).isoformat(), **keys
    )
    after = history(application, gestor, de=(day + datetime.timedelta(days=1)).isoformat(), **keys)

    assert inside["total"] >= 5
    assert before["total"] == 0
    assert after["total"] == 0


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"de": "2026-05-02", "ate": "2026-05-01"}, "de"),
        ({"entidade_id": str(uuid.uuid4())}, "entidade_tipo"),
        ({"entidade_tipo": "desconhecido"}, "entidade_tipo"),
    ],
)
def test_AC_0007_08_an_invalid_filter_is_named(
    application: TestClient, gestor: dict[str, str], params: dict[str, str], field: str
) -> None:
    """An invalid filter is refused and the field named."""
    response = application.get(HIST, params=params, headers=gestor)

    assert response.status_code == 422
    assert error(response)["code"] == "INVALID_DATA"
    assert field in error(response)["fields"]


# ── AC-0007-09 ─ the servidor does not read the whole history ────────────────


def test_AC_0007_09_a_servidor_is_refused(
    application: TestClient, servidor: dict[str, str]
) -> None:
    """A servidor does not read the whole history."""
    response = application.get(HIST, headers=servidor)

    assert response.status_code == 403
    assert error(response)["code"] == "PERFIL_NAO_AUTORIZADO"


def test_AC_0007_09_gestor_and_auditor_read_it(
    application: TestClient, gestor: dict[str, str], auditor: dict[str, str]
) -> None:
    """The gestor and the auditor read the history."""
    assert history(application, gestor)["page"] == 1
    assert history(application, auditor)["size"] == 25
