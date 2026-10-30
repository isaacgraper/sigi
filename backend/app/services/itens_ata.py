"""The items of an ATA and the aditivo de quantidade (SPEC-0003 §3.5, §3.6).

Items are written where the ATA is, by the gestor (AC-0002-05), on the ATAs an
edit is allowed on (AC-0002-24). The unit price keeps five places and nothing
else does; an item's value is derived and rounded once, half up, to the centavo
(ADR-0016, AC-0003-21).
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.atas import ADITIVO_CEILING, NOT_EDITABLE_STATUS
from app.constants.insumos import (
    CENTAVO,
    IMPORT_JUSTIFICATION,
    IMPORT_MESSAGES,
    ITEM_EDITABLE_COLUMN,
    ITEMS_OPTIONAL,
    ITEMS_REQUIRED,
    QUANTITY_PLACES,
    UNIT_PRICE_PLACES,
)
from app.constants.notas_empenho import LOCKED_ITEM_FIELDS, LOCKS_ITEM
from app.core import cnpj as cnpj_lib
from app.models.ata import Ata, AtaAditivo
from app.models.fornecedor import Fornecedor
from app.models.insumo import Insumo, ItemAta
from app.models.user import User
from app.repositories import ata as repo_ata
from app.repositories import insumo as repo_insumo
from app.repositories import item_ata as repo
from app.repositories import nota_empenho as ne_repo
from app.services import importacao
from app.services.atas import FornecedorInput, audit_ata, find_or_create_fornecedor, lock_ata
from app.services.errors import (
    AditivoDeQuantidadeAcimaDoLimite,
    AtaNaoEditavel,
    AtaNaoVigente,
    AtaNotFound,
    InsumoDescontinuado,
    InvalidData,
    ItemAtaComNe,
    ItemAtaDuplicado,
    ItemAtaNotFound,
)
from app.services.insumos import Scope, scope_of, status_of, visible


@dataclass(frozen=True)
class ItemView:
    """An item with its insumo, its effective fornecedor and what is derived from it."""

    item: ItemAta
    insumo: Insumo
    fornecedor: Fornecedor
    contracted_quantity: decimal.Decimal
    total_value: decimal.Decimal


@dataclass(frozen=True)
class ItemsView:
    """An ATA's items with their sum beside the ATA's valor_total (AC-0003-22)."""

    items: Sequence[ItemView]
    items_value: decimal.Decimal
    total_value: decimal.Decimal


@dataclass(frozen=True)
class ItemsLine:
    """One line of an items file as it is written, and what the import does to it (AC-0003-33)."""

    line: int
    sku: str
    description: str
    quantity: decimal.Decimal
    unit_price: decimal.Decimal
    item_number: str | None
    fornecedor: str | None
    action: str


@dataclass(frozen=True)
class ItemsReport:
    """What an items import did, or would do with `dry_run` (AC-0003-26)."""

    lines: tuple[ItemsLine, ...]
    added: int
    corrected: int
    unchanged: int
    ignored_columns: tuple[str, ...]
    dry_run: bool


def item_value(quantity: decimal.Decimal, unit_price: decimal.Decimal) -> decimal.Decimal:
    """`quantity × unit_price`, exact, then rounded half up to the centavo once (ADR-0016)."""
    return (quantity * unit_price).quantize(CENTAVO, rounding=decimal.ROUND_HALF_UP)


def list_items(session: Session, ata_id: uuid.UUID, *, actor: User) -> ItemsView:
    """The ATA's items, by numero_item then SKU; a servidor sees its grupos only (AC-0003-22)."""
    ata = repo_ata.by_id(session, ata_id)
    if ata is None:
        raise AtaNotFound()
    return _items_view(session, ata, scope_of(session, actor))


def add_item(
    session: Session,
    *,
    actor: User,
    ata_id: uuid.UUID,
    insumo_id: uuid.UUID,
    quantity: decimal.Decimal,
    unit_price: decimal.Decimal,
    item_number: str | None,
    fornecedor: FornecedorInput | None,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> ItemAta:
    """Add an insumo to an ATA with its quantity and unit price (AC-0003-17, -20, -23)."""
    ata = _lock_editable(session, ata_id)
    insumo = _active_insumo(session, insumo_id)
    if repo.item_for_insumo(session, ata.id, insumo.id) is not None:
        raise ItemAtaDuplicado()
    item = ItemAta(
        ata_id=ata.id,
        insumo_id=insumo.id,
        fornecedor_id=_override(session, ata, fornecedor),
        item_number=item_number,
        quantity=quantity,
        unit_price=unit_price,
        criado_em=at,
        atualizado_em=at,
    )
    try:
        with session.begin_nested():
            repo.add_item(session, item)
    except IntegrityError as exc:
        raise ItemAtaDuplicado() from exc
    audit_ata(
        session,
        ata,
        "ata.item_adicionado",
        actor,
        correlation_id,
        at,
        previous={"item_ata_id": item.id, "sku": insumo.sku},
    )
    return item


def edit_item(
    session: Session,
    *,
    actor: User,
    ata_id: uuid.UUID,
    item_id: uuid.UUID,
    changes: dict[str, Any],
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> ItemAta:
    """Correct an item: insumo, quantity, price, numero_item or fornecedor (AC-0003-23, -24).

    `fornecedor` set to None clears the item's own and it reads as the ATA's.
    """
    ata = _lock_editable(session, ata_id)
    item = _item(session, ata.id, item_id)
    if "fornecedor" in changes:
        changes["fornecedor_id"] = _override(session, ata, changes.pop("fornecedor"))
    effective = {key: value for key, value in changes.items() if getattr(item, key) != value}
    if not effective:
        return item
    if LOCKED_ITEM_FIELDS & effective.keys():
        _require_unlocked(session, item)
    if "insumo_id" in effective:
        insumo = _active_insumo(session, effective["insumo_id"])
        if repo.item_for_insumo(session, ata.id, insumo.id) is not None:
            raise ItemAtaDuplicado()
    if "quantity" in effective:
        _require_ceiling(session, item, effective["quantity"], extra=decimal.Decimal(0))

    previous = {ITEM_EDITABLE_COLUMN[key]: getattr(item, key) for key in effective}
    previous["item_ata_id"] = item.id
    for key, value in effective.items():
        setattr(item, key, value)
    item.atualizado_em = at
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise ItemAtaDuplicado() from exc
    audit_ata(session, ata, "ata.item_editado", actor, correlation_id, at, previous=previous)
    return item


def remove_item(
    session: Session,
    *,
    actor: User,
    ata_id: uuid.UUID,
    item_id: uuid.UUID,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> None:
    """Remove an item by a date, keeping its row for the history (AC-0003-24)."""
    ata = _lock_editable(session, ata_id)
    item = _item(session, ata.id, item_id)
    _require_unlocked(session, item)
    insumo = repo_insumo.insumo_by_id(session, item.insumo_id)
    previous = {
        "item_ata_id": item.id,
        "sku": insumo.sku if insumo else None,
        "quantidade": item.quantity,
        "valor_unitario": item.unit_price,
        "numero_item": item.item_number,
        "fornecedor_id": item.fornecedor_id,
    }
    item.removed_at = at
    item.atualizado_em = at
    session.flush()
    audit_ata(session, ata, "ata.item_removido", actor, correlation_id, at, previous=previous)


def add_quantity_aditivo(
    session: Session,
    *,
    actor: User,
    ata_id: uuid.UUID,
    item_id: uuid.UUID | None,
    quantity: decimal.Decimal | None,
    justification: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> AtaAditivo:
    """Raise one item's contracted quantity, at most 25% of its own (AC-0003-27, -28, RN15)."""
    ata = lock_ata(session, ata_id)
    if ata.status != "vigente":
        raise AtaNaoVigente()
    if item_id is None:
        raise InvalidData({"item_id": "Escolha o item."})
    if quantity is None or quantity <= 0:
        raise InvalidData({"quantity": "Informe uma quantidade maior que zero."})
    item = _item(session, ata.id, item_id)
    already = repo.aditivos_de_quantidade(session, [item.id]).get(item.id, decimal.Decimal(0))
    _require_ceiling(session, item, item.quantity, extra=quantity)

    aditivo = repo_ata.add_aditivo(
        session,
        AtaAditivo(
            ata_id=ata.id,
            kind="quantidade",
            item_ata_id=item.id,
            quantidade_acrescimo=quantity,
            justification=justification,
            created_by=actor.id,
            criado_em=at,
        ),
    )
    audit_ata(
        session,
        ata,
        "ata.aditivo_registrado",
        actor,
        correlation_id,
        at,
        previous={"item_ata_id": item.id, "quantidade_contratada": item.quantity + already},
        justification=justification,
    )
    return aditivo


# ── The items file (AC-0003-26) ─────────────────────────────────────────────


@dataclass(frozen=True)
class _ItemRow:
    line: int
    insumo: Insumo
    quantity: decimal.Decimal
    unit_price: decimal.Decimal
    item_number: str | None
    fornecedor: FornecedorInput | None


def _items_line(
    session: Session,
    row: _ItemRow,
    fornecedor_id: uuid.UUID | None,
    item_number: str | None,
    action: str,
) -> ItemsLine:
    """The line as stored; the fornecedor named only when it is not the ATA's own."""
    fornecedor = repo_ata.fornecedor_by_id(session, fornecedor_id) if fornecedor_id else None
    return ItemsLine(
        line=row.line,
        sku=row.insumo.sku,
        description=row.insumo.description,
        quantity=row.quantity,
        unit_price=row.unit_price,
        item_number=item_number,
        fornecedor=fornecedor.legal_name if fornecedor else None,
        action=action,
    )


def import_items(
    session: Session,
    *,
    actor: User,
    ata_id: uuid.UUID,
    content: bytes,
    dry_run: bool,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> ItemsReport:
    """Add or correct an ATA's items by SKU from a file, all or nothing (AC-0003-26).

    The file does not create insumos: a SKU that is not in the catalogue is a line
    to fix, not a new entry made by accident. Items not in the file are left as
    they are.
    """
    ata = _lock_editable(session, ata_id)
    sheet = importacao.read(content, required=ITEMS_REQUIRED, optional=ITEMS_OPTIONAL)
    report = importacao.Report.of(sheet)
    catalogue = repo_insumo.insumos_by_sku(
        session, {cells.get("sku", "").upper() for _, cells in sheet.lines}
    )
    current = {item.insumo_id: item for item in repo.items_of(session, ata.id)}
    aditivos = repo.aditivos_de_quantidade(session, [item.id for item in current.values()])

    rows: list[_ItemRow] = []
    first_line: dict[str, int] = {}
    for line, cells in sheet.lines:
        before = len(report.rows)
        for column in ITEMS_REQUIRED:
            if not cells.get(column):
                report.error(line, column, IMPORT_MESSAGES["required"])
        sku = cells.get("sku", "").upper()
        insumo = catalogue.get(sku)
        if sku and insumo is None:
            report.error(line, "sku", IMPORT_MESSAGES["sku_unknown"])
        elif insumo is not None and insumo.id not in current and status_of(insumo) != "ativo":
            report.error(line, "sku", IMPORT_MESSAGES["descontinuado"])
        if sku in first_line:
            other = first_line[sku]
            report.error(line, "sku", IMPORT_MESSAGES["duplicate_sku"].format(other=other))
            report.error(other, "sku", IMPORT_MESSAGES["duplicate_sku"].format(other=line))
        elif sku:
            first_line[sku] = line

        quantity = _cell_number(report, line, cells, "quantidade", sheet, QUANTITY_PLACES)
        unit_price = _cell_number(report, line, cells, "valor_unitario", sheet, UNIT_PRICE_PLACES)

        fornecedor: FornecedorInput | None = None
        cnpj = cells.get("cnpj_fornecedor", "")
        if cnpj:
            if not cnpj_lib.is_valid(cnpj):
                report.error(line, "cnpj_fornecedor", IMPORT_MESSAGES["cnpj"])
            else:
                known = repo_ata.fornecedor_by_cnpj(session, cnpj_lib.normalise(cnpj))
                legal_name = cells.get("razao_social_fornecedor", "")
                if known is None and not legal_name:
                    report.error(line, "razao_social_fornecedor", IMPORT_MESSAGES["razao_social"])
                fornecedor = FornecedorInput(cnpj=cnpj, legal_name=legal_name)

        if insumo is not None and quantity is not None and insumo.id in current:
            held = current[insumo.id]
            if (quantity != held.quantity or unit_price != held.unit_price) and (
                ne_repo.item_referenced_in(session, held.id, LOCKS_ITEM)
            ):
                report.error(line, "quantidade", IMPORT_MESSAGES["com_ne"])
            if aditivos.get(held.id, decimal.Decimal(0)) > quantity * ADITIVO_CEILING:
                report.error(line, "quantidade", IMPORT_MESSAGES["aditivo"])

        if len(report.rows) == before and insumo is not None:
            assert quantity is not None and unit_price is not None
            rows.append(
                _ItemRow(
                    line=line,
                    insumo=insumo,
                    quantity=quantity,
                    unit_price=unit_price,
                    item_number=cells.get("numero_item") or None,
                    fornecedor=fornecedor,
                )
            )
    report.raise_if_any()

    added = corrected = unchanged = 0
    written: list[ItemsLine] = []
    savepoint = session.begin_nested()
    for row in rows:
        fornecedor_id = _override(session, ata, row.fornecedor)
        existing = current.get(row.insumo.id)
        if existing is None:
            written.append(_items_line(session, row, fornecedor_id, row.item_number, "added"))
            item = repo.add_item(
                session,
                ItemAta(
                    ata_id=ata.id,
                    insumo_id=row.insumo.id,
                    fornecedor_id=fornecedor_id,
                    item_number=row.item_number,
                    quantity=row.quantity,
                    unit_price=row.unit_price,
                    criado_em=at,
                    atualizado_em=at,
                ),
            )
            audit_ata(
                session,
                ata,
                "ata.item_adicionado",
                actor,
                correlation_id,
                at,
                previous={"item_ata_id": item.id, "sku": row.insumo.sku},
                justification=IMPORT_JUSTIFICATION,
            )
            added += 1
            continue
        wanted: dict[str, Any] = {"quantity": row.quantity, "unit_price": row.unit_price}
        if row.item_number is not None:
            wanted["item_number"] = row.item_number
        if row.fornecedor is not None:
            wanted["fornecedor_id"] = fornecedor_id
        changes = {k: v for k, v in wanted.items() if getattr(existing, k) != v}
        stored_fornecedor = changes.get("fornecedor_id", existing.fornecedor_id)
        stored_number = changes.get("item_number", existing.item_number)
        if not changes:
            written.append(_items_line(session, row, stored_fornecedor, stored_number, "unchanged"))
            unchanged += 1
            continue
        written.append(_items_line(session, row, stored_fornecedor, stored_number, "corrected"))
        previous = {ITEM_EDITABLE_COLUMN[k]: getattr(existing, k) for k in changes}
        previous["item_ata_id"] = existing.id
        for key, value in changes.items():
            setattr(existing, key, value)
        existing.atualizado_em = at
        session.flush()
        audit_ata(
            session,
            ata,
            "ata.item_editado",
            actor,
            correlation_id,
            at,
            previous=previous,
            justification=IMPORT_JUSTIFICATION,
        )
        corrected += 1
    if dry_run:
        savepoint.rollback()
    else:
        savepoint.commit()
    return ItemsReport(
        lines=tuple(written),
        added=added,
        corrected=corrected,
        unchanged=unchanged,
        ignored_columns=sheet.unknown_columns,
        dry_run=dry_run,
    )


# ── Helpers ─────────────────────────────────────────────────────────────────


def _items_view(session: Session, ata: Ata, scope: Scope) -> ItemsView:
    items = list(repo.items_of(session, ata.id))
    insumos = repo_insumo.insumos_by_id(session, {item.insumo_id for item in items})
    items = [item for item in items if visible(scope, insumos[item.insumo_id])]
    aditivos = repo.aditivos_de_quantidade(session, [item.id for item in items])
    own = repo_ata.fornecedor_by_id(session, ata.fornecedor_id)
    assert own is not None  # the FK guarantees it

    views: list[ItemView] = []
    for item in items:
        fornecedor = own
        if item.fornecedor_id is not None:
            found = repo_ata.fornecedor_by_id(session, item.fornecedor_id)
            fornecedor = found if found is not None else own
        contracted = item.quantity + aditivos.get(item.id, decimal.Decimal(0))
        views.append(
            ItemView(
                item=item,
                insumo=insumos[item.insumo_id],
                fornecedor=fornecedor,
                contracted_quantity=contracted,
                total_value=item_value(contracted, item.unit_price),
            )
        )
    views.sort(key=_order)
    return ItemsView(
        items=views,
        items_value=sum((view.total_value for view in views), decimal.Decimal("0.00")),
        total_value=ata.total_value,
    )


def _order(view: ItemView) -> tuple[bool, int, str, str]:
    """By numero_item read as a number when it is one, then by SKU (AC-0003-22)."""
    number = view.item.item_number
    numeric = number is not None and number.isdigit()
    return (
        number is None,
        int(number) if numeric and number is not None else 0,
        number or "",
        view.insumo.sku,
    )


def _lock_editable(session: Session, ata_id: uuid.UUID) -> Ata:
    ata = lock_ata(session, ata_id)
    if ata.status in NOT_EDITABLE_STATUS:
        raise AtaNaoEditavel()
    return ata


def _require_unlocked(session: Session, item: ItemAta) -> None:
    """An item an NE past demanda carries changes only by an aditivo (AC-0004-27)."""
    if ne_repo.item_referenced_in(session, item.id, LOCKS_ITEM):
        insumo = repo_insumo.insumo_by_id(session, item.insumo_id)
        raise ItemAtaComNe(insumo.description if insumo else str(item.id))


def _item(session: Session, ata_id: uuid.UUID, item_id: uuid.UUID) -> ItemAta:
    item = repo.item_of(session, ata_id, item_id)
    if item is None:
        raise ItemAtaNotFound()
    return item


def _active_insumo(session: Session, insumo_id: uuid.UUID) -> Insumo:
    insumo = repo_insumo.insumo_by_id(session, insumo_id)
    if insumo is None:
        raise InvalidData({"insumo_id": "Insumo não encontrado."})
    if status_of(insumo) != "ativo":
        substitute = (
            repo_insumo.insumo_by_id(session, insumo.substitute_id)
            if insumo.substitute_id
            else None
        )
        raise InsumoDescontinuado(substitute.sku if substitute else None)
    return insumo


def _override(session: Session, ata: Ata, given: FornecedorInput | None) -> uuid.UUID | None:
    """The item's own fornecedor, or None when it is the ATA's (OQ-11)."""
    if given is None:
        return None
    fornecedor = find_or_create_fornecedor(session, given)
    return None if fornecedor.id == ata.fornecedor_id else fornecedor.id


def _require_ceiling(
    session: Session, item: ItemAta, quantity: decimal.Decimal, *, extra: decimal.Decimal
) -> None:
    """The aditivos de quantidade, with `extra`, may not pass 25% of `quantity` (AC-0003-28)."""
    already = repo.aditivos_de_quantidade(session, [item.id]).get(item.id, decimal.Decimal(0))
    if already + extra > quantity * ADITIVO_CEILING:
        raise AditivoDeQuantidadeAcimaDoLimite()


def _cell_number(
    report: importacao.Report,
    line: int,
    cells: dict[str, str],
    column: str,
    sheet: importacao.Sheet,
    places: int,
) -> decimal.Decimal | None:
    if not cells.get(column):
        return None
    try:
        return importacao.number(cells[column], separator=sheet.separator, places=places)
    except importacao.CellError as exc:
        report.error(line, column, str(exc))
        return None
