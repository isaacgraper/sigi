"""Migration `0003_atas` — what the schema guarantees for SPEC-0002.

These prove the schema rather than an AC: the database refuses what the service
also refuses, so a second writer cannot bypass the service, and the application
role cannot delete an ATA (AC-0002-17).
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

APP_ROLE = "sigi_app_test"
TABLES = ("fornecedor", "ata", "ata_aditivo", "ata_reajuste")


def _usuario(connection: psycopg.Connection) -> uuid.UUID:
    uid = uuid.uuid4()
    connection.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'Gestora', %s, 'gestor', 'ativo')",
        (uid, f"g-{uid.hex[:8]}@sc.gov.br"),
    )
    return uid


def _fornecedor(connection: psycopg.Connection) -> uuid.UUID:
    fid = uuid.uuid4()
    connection.execute(
        "INSERT INTO fornecedor (id, cnpj, razao_social) VALUES (%s, %s, 'Empresa')",
        (fid, str(int(uuid.uuid4().int % 10**14)).zfill(14)),
    )
    return fid


def _ata(connection: psycopg.Connection, **override: object) -> uuid.UUID:
    values: dict[str, object] = {
        "numero": f"ATA-{uuid.uuid4().hex[:10]}",
        "vigencia_inicio": "2026-01-01",
        "vigencia_fim": "2026-12-31",
        "valor_total": "100.00",
        "status": "rascunho",
    }
    values.update(override)
    ata_id = uuid.uuid4()
    connection.execute(
        "INSERT INTO ata (id, numero, objeto, orgao, fornecedor_id, vigencia_inicio,"
        " vigencia_fim, valor_total, data_orcamento_planilhado, status, responsavel_id)"
        " VALUES (%s, %s, 'Objeto', 'Órgão', %s, %s, %s, %s, '2026-03-01', %s, %s)",
        (
            ata_id,
            values["numero"],
            _fornecedor(connection),
            values["vigencia_inicio"],
            values["vigencia_fim"],
            values["valor_total"],
            values["status"],
            _usuario(connection),
        ),
    )
    return ata_id


@pytest.mark.parametrize("table", TABLES)
def test_the_application_role_can_read_write_but_never_delete(
    admin_connection: psycopg.Connection, table: str
) -> None:
    """AC-0002-17 — withholding DELETE is what makes "never deleted" a fact about the schema."""
    privileges = {
        privilege: admin_connection.execute(
            "SELECT has_table_privilege(%s, %s, %s)", (APP_ROLE, table, privilege)
        ).fetchone()[0]  # type: ignore[index]
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE")
    }
    assert privileges == {"SELECT": True, "INSERT": True, "UPDATE": True, "DELETE": False}


def test_a_vigencia_that_does_not_end_after_it_starts_is_refused(
    admin_connection: psycopg.Connection,
) -> None:
    """AC-0002-03 — `ck_ata_vigencia`."""
    with pytest.raises(psycopg.errors.CheckViolation):
        _ata(admin_connection, vigencia_fim="2026-01-01")


@pytest.mark.parametrize("value", ["0", "-1.00"])
def test_a_valor_that_is_not_positive_is_refused(
    admin_connection: psycopg.Connection, value: str
) -> None:
    """AC-0002-04 — `ck_ata_valor_positivo`."""
    with pytest.raises(psycopg.errors.CheckViolation):
        _ata(admin_connection, valor_total=value)


def test_an_unknown_status_is_refused(admin_connection: psycopg.Connection) -> None:
    """AC-0002-22 — `ck_ata_status`."""
    with pytest.raises(psycopg.errors.CheckViolation):
        _ata(admin_connection, status="aprovada")


def test_a_numero_cannot_repeat(admin_connection: psycopg.Connection) -> None:
    """AC-0002-02 — the database refuses a second ATA with the same numero."""
    number = f"ATA-{uuid.uuid4().hex[:10]}"
    _ata(admin_connection, numero=number)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _ata(admin_connection, numero=number)


@pytest.mark.parametrize(
    "tipo,valor,fim",
    [
        ("valor", None, None),
        ("valor", "10.00", "2027-01-01"),
        ("prazo", "10.00", "2027-01-01"),
        ("prazo", None, None),
        ("quantidade", "10.00", None),
    ],
)
def test_an_aditivo_carries_the_figure_of_its_kind_and_not_the_other(
    admin_connection: psycopg.Connection, tipo: str, valor: str | None, fim: str | None
) -> None:
    """AC-0002-13 — `ck_ata_aditivo_campos` and `ck_ata_aditivo_tipo`."""
    ata_id = _ata(admin_connection)
    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute(
            "INSERT INTO ata_aditivo (ata_id, tipo, valor_acrescimo, nova_vigencia_fim,"
            " justificativa, criado_por) VALUES (%s, %s, %s, %s, 'x', %s)",
            (ata_id, tipo, valor, fim, _usuario(admin_connection)),
        )


@pytest.mark.parametrize("cnpj", ["123", "1122233300018A", "11.222.333/0001-81"])
def test_a_cnpj_is_stored_as_fourteen_digits(
    admin_connection: psycopg.Connection, cnpj: str
) -> None:
    """AC-0002-25 — `ck_fornecedor_cnpj` and the column width: punctuation is never stored."""
    with pytest.raises((psycopg.errors.CheckViolation, psycopg.errors.StringDataRightTruncation)):
        admin_connection.execute(
            "INSERT INTO fornecedor (cnpj, razao_social) VALUES (%s, 'Empresa')", (cnpj,)
        )
