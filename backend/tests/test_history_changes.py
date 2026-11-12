"""What each event changed, derived without a database — SPEC-0007 v1.1, AC-0007-10.

The walk starts from the entity as it is now and rewinds it row by row, so these
tests hand it a state and the rows that led to it.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from typing import Any

from app.services.history_changes import Change, Detail, Entry, EventChanges, walk

T0 = datetime.datetime(2026, 11, 1, 12, 0, tzinfo=datetime.UTC)


def entry(minutes: int, acao: str, dados: dict[str, Any] | None = None, **kw: Any) -> Entry:
    """A row `minutes` after T0."""
    return Entry(
        id=uuid.uuid4(),
        acao=acao,
        ocorrido_em=T0 + datetime.timedelta(minutes=minutes),
        dados=dados,
        **kw,
    )


def changed(event: EventChanges) -> dict[str, tuple[Any, Any]]:
    """The changes of an event as campo → (antes, depois)."""
    return {c.campo: (c.antes, c.depois) for c in event.alteracoes}


def detailed(event: EventChanges) -> dict[str, Any]:
    """The details of an event as campo → valor."""
    return {d.campo: d.valor for d in event.detalhes}


ATA_NOW = {
    "numero": "ATA-1",
    "objeto": "Material de expediente",
    "orgao": "Secretaria de Saúde",
    "fornecedor_id": str(uuid.UUID(int=1)),
    "data_emissao": None,
    "vigencia_inicio": "2026-01-01",
    "vigencia_fim": "2028-01-01",
    "valor_total": "100000.00",
    "data_orcamento_planilhado": "2026-03-10",
    "status": "vigente",
    "responsavel_id": str(uuid.UUID(int=2)),
}


def test_AC_0007_10_an_aditivo_de_prazo_then_an_edit_chain_their_values() -> None:
    """Each "after" is the next row's "before", and the newest one's is the live value."""
    criada = entry(0, "ata.criada")
    aditivo = entry(1, "ata.aditivo_registrado", {"vigencia_fim": "2026-12-31"})
    editada = entry(2, "ata.editada", {"vigencia_fim": "2027-03-31"})

    result = walk("ata", [criada, aditivo, editada], ATA_NOW)

    assert result[editada.id].acao_rotulo == "ATA corrigida"
    assert result[editada.id].alteracoes == (
        Change("vigencia_fim", "Fim da vigência", "data", "2027-03-31", "2028-01-01"),
    )
    assert result[aditivo.id].acao_rotulo == "Aditivo registrado"
    assert changed(result[aditivo.id]) == {"vigencia_fim": ("2026-12-31", "2027-03-31")}


def test_AC_0007_10_a_creation_lists_the_values_it_was_created_with() -> None:
    """A creation reads "criado com": every field it set, with no value before."""
    criada = entry(0, "ata.criada")
    editada = entry(1, "ata.editada", {"objeto": "Material de limpeza"})

    result = walk("ata", [criada, editada], ATA_NOW)

    created = changed(result[criada.id])
    assert created["objeto"] == (None, "Material de limpeza")
    assert created["vigencia_fim"] == (None, "2028-01-01")
    assert created["valor_total"] == (None, "100000")
    assert "data_emissao" not in created
    assert all(antes is None for antes, _ in created.values())


def test_AC_0007_10_an_aditivo_de_valor_adds_its_acrescimo() -> None:
    """The row keeps the total before; the "after" adds the acréscimo of `ata_aditivo`."""
    aditivo = entry(
        1,
        "ata.aditivo_registrado",
        {"valor_contratado": "100000.00"},
        acrescimo=decimal.Decimal("5000.50"),
    )

    result = walk("ata", [entry(0, "ata.criada"), aditivo], ATA_NOW)

    assert result[aditivo.id].alteracoes == (
        Change("valor_contratado", "Valor contratado", "dinheiro", "100000", "105000.5"),
    )


def test_AC_0007_10_an_aditivo_de_quantidade_adds_its_acrescimo_to_the_item() -> None:
    """The item's quantidade contratada, before and after the acréscimo."""
    item_id = str(uuid.uuid4())
    aditivo = entry(
        1,
        "ata.aditivo_registrado",
        {"item_ata_id": item_id, "quantidade_contratada": "10.000"},
        acrescimo=decimal.Decimal("2.5"),
    )
    state = {"numero_item": "1", "insumo_id": item_id, "quantidade": "10", "valor_unitario": "5"}

    result = walk("item_ata", [aditivo], state)

    assert changed(result[aditivo.id]) == {"quantidade_contratada": ("10", "12.5")}
    assert detailed(result[aditivo.id]) == {"item_ata_id": item_id}


def test_AC_0007_10_a_removal_lists_the_values_it_removed() -> None:
    """A removal has no value after; the item it removed reads as created before it."""
    item_id = str(uuid.uuid4())
    adicionado = entry(0, "ata.item_adicionado", {"item_ata_id": item_id, "sku": "SKU-1"})
    removido = entry(
        1,
        "ata.item_removido",
        {
            "item_ata_id": item_id,
            "sku": "SKU-1",
            "quantidade": "10.000",
            "valor_unitario": "5.00",
            "numero_item": "1",
        },
    )
    state = {
        "numero_item": "1",
        "insumo_id": str(uuid.UUID(int=3)),
        "fornecedor_id": None,
        "quantidade": "10.000",
        "valor_unitario": "5.00",
        "removido_em": "2026-11-01T12:01:00+00:00",
    }

    result = walk("item_ata", [adicionado, removido], state)

    assert result[removido.id].acao_rotulo == "Item removido"
    assert changed(result[removido.id]) == {
        "quantidade": ("10", None),
        "valor_unitario": ("5", None),
        "numero_item": ("1", None),
    }
    assert detailed(result[removido.id]) == {"item_ata_id": item_id, "sku": "SKU-1"}
    assert changed(result[adicionado.id])["quantidade"] == (None, "10")


def test_AC_0007_10_an_ne_advance_shows_the_numero_it_set() -> None:
    """The número of a stage is set with no prior value recorded: it reads null before."""
    avancada = entry(0, "ne.avancada", {"status": "validacao_saldo", "valor_reservado_ata": "0"})
    state = {"status": "pre_empenho", "numero_pre_empenho": "PE-2026-1", "processo_sei": "x"}

    result = walk("nota_empenho", [avancada], state)

    assert changed(result[avancada.id]) == {
        "status": ("validacao_saldo", "pre_empenho"),
        "numero_pre_empenho": (None, "PE-2026-1"),
    }
    assert detailed(result[avancada.id]) == {"valor_reservado_ata": "0"}
    assert result[avancada.id].detalhes[0] == Detail(
        "valor_reservado_ata", "Valor reservado na ATA", "0"
    )


def test_AC_0007_10_a_refused_advance_changes_nothing() -> None:
    """`ne.bloqueada` carries details only, and the walk goes past it untouched."""
    avancada = entry(0, "ne.avancada", {"status": "demanda"})
    bloqueada = entry(
        1,
        "ne.bloqueada",
        {"status": "validacao_saldo", "motivo": "Saldo insuficiente.", "saldo_disponivel": "10"},
    )
    state = {"status": "validacao_saldo"}

    result = walk("nota_empenho", [avancada, bloqueada], state)

    assert result[bloqueada.id].alteracoes == ()
    assert detailed(result[bloqueada.id])["saldo_disponivel"] == "10"
    assert changed(result[avancada.id]) == {"status": ("demanda", "validacao_saldo")}


def test_AC_0007_10_a_quarentena_shows_its_motivo_and_its_release() -> None:
    """Holding and releasing an NF: the flag and the motivo, before and after."""
    iniciada = entry(0, "nf.quarentena_iniciada", {"motivo": "Caixa avariada."})
    liberada = entry(1, "nf.quarentena_liberada", {"motivo": "Caixa avariada."})
    state = {"status": "aguardando_conferencia", "quarentena": False, "motivo_quarentena": None}

    result = walk("nota_fiscal", [iniciada, liberada], state)

    assert changed(result[liberada.id]) == {
        "quarentena": (True, False),
        "motivo_quarentena": ("Caixa avariada.", None),
    }
    assert changed(result[iniciada.id]) == {
        "quarentena": (False, True),
        "motivo_quarentena": (None, "Caixa avariada."),
    }
    assert detailed(result[iniciada.id]) == {"motivo": "Caixa avariada."}


def test_AC_0007_10_changed_itens_read_before_and_after() -> None:
    """The lines of an NE, compared as numbers, before and after."""
    item_id = str(uuid.uuid4())
    alterados = entry(
        0, "ne.itens_alterados", {"itens": [{"item_ata_id": item_id, "quantidade": "200"}]}
    )
    state = {"status": "demanda", "itens": [{"item_ata_id": item_id, "quantidade": "300.000"}]}

    result = walk("nota_empenho", [alterados], state)

    assert result[alterados.id].alteracoes == (
        Change(
            "itens",
            "Itens",
            "itens",
            [{"item_ata_id": item_id, "quantidade": "200"}],
            [{"item_ata_id": item_id, "quantidade": "300"}],
        ),
    )


def test_AC_0007_10_a_field_recorded_but_unchanged_is_a_detail() -> None:
    """A value written back as it was is context, not a change."""
    editada = entry(0, "ata.editada", {"valor_total": "100000", "objeto": "Antigo"})

    result = walk("ata", [editada], {**ATA_NOW, "objeto": "Novo"})

    assert changed(result[editada.id]) == {"objeto": ("Antigo", "Novo")}
    assert detailed(result[editada.id]) == {"valor_total": "100000"}


def test_AC_0007_10_an_entity_with_no_state_carries_only_details() -> None:
    """A usuario, a refused route or an unknown acao: labelled details, no changes."""
    bloqueado = entry(0, "usuario.bloqueado", {"status": "ativo"})
    unknown = entry(1, "usuario.algo_novo", {"alvo_id": "x"})

    result = walk("usuario", [bloqueado, unknown], None)

    assert result[bloqueado.id] == EventChanges(
        "Membro bloqueado", (), (Detail("status", "Status", "ativo"),)
    )
    assert result[unknown.id].acao_rotulo == "usuario.algo_novo"
    assert result[unknown.id].detalhes == (Detail("alvo_id", "Membro", "x"),)
