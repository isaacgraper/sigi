"""Migration `0005_insumos`: what the schema guarantees on its own.

These prove the schema rather than an AC: the database refuses what the service
also refuses, so a second writer cannot bypass the service, and the application
role cannot delete an insumo or an item (AC-0003-10, -24).
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

APP_ROLE = "sigi_app_test"


def _grupo(connection: psycopg.Connection, *, parent: uuid.UUID | None = None) -> uuid.UUID:
    gid = uuid.uuid4()
    connection.execute(
        "INSERT INTO grupo_material (id, nome, nivel, grupo_pai_id) VALUES (%s, %s, %s, %s)",
        (gid, f"G {gid.hex[:8]}", 1 if parent is None else 2, parent),
    )
    return gid


def _insumo(connection: psycopg.Connection, **override: object) -> uuid.UUID:
    values: dict[str, object] = {"sku": f"M{uuid.uuid4().hex[:10].upper()}", "codigo_doms": None}
    values.update(override)
    iid = uuid.uuid4()
    connection.execute(
        "INSERT INTO insumo (id, sku, codigo_doms, descricao, unidade, grupo_id)"
        " VALUES (%s, %s, %s, 'Descrição', 'UN', %s)",
        (iid, values["sku"], values["codigo_doms"], _grupo(connection)),
    )
    return iid


@pytest.mark.parametrize("table", ["grupo_material", "insumo", "item_ata"])
def test_the_application_role_can_read_write_but_never_delete(
    admin_connection: psycopg.Connection, table: str
) -> None:
    """AC-0003-10, -24 — an insumo is discontinued and an item removed by a date, never deleted."""
    privileges = {
        privilege: admin_connection.execute(
            "SELECT has_table_privilege(%s, %s, %s)", (APP_ROLE, table, privilege)
        ).fetchone()[0]  # type: ignore[index]
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE")
    }
    assert privileges == {"SELECT": True, "INSERT": True, "UPDATE": True, "DELETE": False}


def test_a_servidors_grupos_are_a_set_replaced_whole(admin_connection: psycopg.Connection) -> None:
    """AC-0003-30 — the one table the role may delete from, and may not update."""
    privileges = {
        privilege: admin_connection.execute(
            "SELECT has_table_privilege(%s, 'usuario_grupo_material', %s)", (APP_ROLE, privilege)
        ).fetchone()[0]  # type: ignore[index]
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE")
    }
    assert privileges == {"SELECT": True, "INSERT": True, "UPDATE": False, "DELETE": True}


@pytest.mark.parametrize("sku", ["com-hifen", "COM ESPACO", "MINÚSCULO", "X.Y"])
def test_the_database_refuses_a_malformed_sku(
    admin_connection: psycopg.Connection, sku: str
) -> None:
    """AC-0003-02 in the schema, for the default pattern."""
    with pytest.raises(psycopg.errors.CheckViolation):
        _insumo(admin_connection, sku=sku)


def test_the_database_refuses_a_float_doms_code(admin_connection: psycopg.Connection) -> None:
    """AC-0003-02 in the schema — `2888.0` does not fit."""
    with pytest.raises(psycopg.errors.CheckViolation):
        _insumo(admin_connection, codigo_doms="2888.0")


def test_the_database_keeps_the_sku_and_doms_code_unique(
    admin_connection: psycopg.Connection,
) -> None:
    """AC-0003-03 in the schema."""
    code = str(uuid.uuid4().int % 10**10)
    first = _insumo(admin_connection, codigo_doms=code)
    sku = admin_connection.execute("SELECT sku FROM insumo WHERE id = %s", (first,)).fetchone()[0]  # type: ignore[index]
    with pytest.raises(psycopg.errors.UniqueViolation):
        _insumo(admin_connection, sku=sku)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _insumo(admin_connection, codigo_doms=code)


def test_the_database_keeps_grupos_in_three_levels(admin_connection: psycopg.Connection) -> None:
    """AC-0003-09 in the schema — a level 1 has no parent, nothing is level 4, siblings differ."""
    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute("INSERT INTO grupo_material (nome, nivel) VALUES ('Quarto', 4)")
    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute(
            "INSERT INTO grupo_material (nome, nivel, grupo_pai_id) VALUES ('Raiz', 1, %s)",
            (_grupo(admin_connection),),
        )
    name = f"Raiz {uuid.uuid4().hex[:8]}"
    admin_connection.execute("INSERT INTO grupo_material (nome, nivel) VALUES (%s, 1)", (name,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        admin_connection.execute(
            "INSERT INTO grupo_material (nome, nivel) VALUES (%s, 1)", (name.upper(),)
        )


def test_a_substitute_implies_a_discontinuation(admin_connection: psycopg.Connection) -> None:
    """AC-0003-15 in the schema — pointing to a substitute without a date is refused."""
    old, new = _insumo(admin_connection), _insumo(admin_connection)
    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute(
            "UPDATE insumo SET substituido_por_id = %s WHERE id = %s", (new, old)
        )
    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute(
            "UPDATE insumo SET substituido_por_id = id, descontinuado_em = current_date"
            " WHERE id = %s",
            (old,),
        )


def test_the_unit_price_keeps_five_places(admin_connection: psycopg.Connection) -> None:
    """ADR-0016 — `valor_unitario` is NUMERIC(15,5); every other money column is (15,2)."""
    row = admin_connection.execute(
        "SELECT numeric_precision, numeric_scale FROM information_schema.columns"
        " WHERE table_name = 'item_ata' AND column_name = 'valor_unitario'"
    ).fetchone()
    assert row == (15, 5)


def _item(connection: psycopg.Connection) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """An ATA, an item of it, and the gestor who registered it."""
    uid, fid, ata, item = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    connection.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'Gestora', %s, 'gestor', 'ativo')",
        (uid, f"g-{uid.hex[:8]}@sc.gov.br"),
    )
    connection.execute(
        "INSERT INTO fornecedor (id, cnpj, razao_social) VALUES (%s, %s, 'Empresa')",
        (fid, str(uuid.uuid4().int % 10**14).zfill(14)),
    )
    connection.execute(
        "INSERT INTO ata (id, numero, objeto, orgao, fornecedor_id, vigencia_inicio,"
        " vigencia_fim, valor_total, data_orcamento_planilhado, responsavel_id)"
        " VALUES (%s, %s, 'Objeto', 'Órgão', %s, '2026-01-01', '2026-12-31', 100,"
        " '2026-03-01', %s)",
        (ata, f"ATA-{ata.hex[:10]}", fid, uid),
    )
    connection.execute(
        "INSERT INTO item_ata (id, ata_id, insumo_id, quantidade, valor_unitario)"
        " VALUES (%s, %s, %s, 100, 1.5)",
        (item, ata, _insumo(connection)),
    )
    return ata, item, uid


@pytest.mark.parametrize(
    ("tipo", "valor", "item", "quantidade"),
    [
        ("quantidade", None, False, "5"),
        ("quantidade", None, True, None),
        ("quantidade", None, True, "0"),
        ("quantidade", "10.00", True, "5"),
        ("valor", "10.00", True, None),
        ("prazo", None, True, None),
    ],
)
def test_an_aditivo_de_quantidade_carries_its_item_and_nothing_else(
    admin_connection: psycopg.Connection,
    tipo: str,
    valor: str | None,
    item: bool,
    quantidade: str | None,
) -> None:
    """AC-0003-27 in the schema — a quantity aditivo names an item and a positive quantity."""
    ata, item_id, uid = _item(admin_connection)
    with pytest.raises(psycopg.errors.CheckViolation):
        admin_connection.execute(
            "INSERT INTO ata_aditivo (ata_id, tipo, valor_acrescimo, nova_vigencia_fim,"
            " item_ata_id, quantidade_acrescimo, justificativa, criado_por)"
            " VALUES (%s, %s, %s, %s, %s, %s, 'Motivo', %s)",
            (
                ata,
                tipo,
                valor,
                "2027-12-31" if tipo == "prazo" else None,
                item_id if item else None,
                quantidade,
                uid,
            ),
        )


def test_a_well_formed_aditivo_de_quantidade_is_accepted(
    admin_connection: psycopg.Connection,
) -> None:
    """AC-0003-27 in the schema — the positive control for the refusals above."""
    ata, item_id, uid = _item(admin_connection)
    admin_connection.execute(
        "INSERT INTO ata_aditivo (ata_id, tipo, item_ata_id, quantidade_acrescimo,"
        " justificativa, criado_por) VALUES (%s, 'quantidade', %s, 20, 'Motivo', %s)",
        (ata, item_id, uid),
    )


def test_an_insumo_is_an_item_of_an_ata_once_while_not_removed(
    admin_connection: psycopg.Connection,
) -> None:
    """AC-0003-20, -24 in the schema — a removed item frees its insumo."""
    ata, item_id, _ = _item(admin_connection)
    insumo = admin_connection.execute(
        "SELECT insumo_id FROM item_ata WHERE id = %s", (item_id,)
    ).fetchone()[0]  # type: ignore[index]
    insert = (
        "INSERT INTO item_ata (ata_id, insumo_id, quantidade, valor_unitario) VALUES (%s, %s, 1, 1)"
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        admin_connection.execute(insert, (ata, insumo))
    admin_connection.execute("UPDATE item_ata SET removido_em = now() WHERE id = %s", (item_id,))
    admin_connection.execute(insert, (ata, insumo))
