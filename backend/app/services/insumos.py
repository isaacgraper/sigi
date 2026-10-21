"""The insumo catalogue, its grupos and the servidor's scope (SPEC-0003 §3.1 to §3.4, §3.7).

The SKU is the identity (RN14). An insumo leaves the catalogue by being
discontinued or substituted, never deleted, so every ATA, NE and NF that
referenced it stays readable (AC-0003-10). Its situação is derived from
`descontinuado_em` and `substituido_por_id` and has no column.

RN07 limits what a servidor sees to the grupos it owns and those below them. A
scope of `None` means unrestricted: the gestor and the auditor (AC-0003-29).
"""

from __future__ import annotations

import datetime
import decimal
import re
import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.insumos import (
    CATALOGUE_OPTIONAL,
    CATALOGUE_REQUIRED,
    DOMS_CODE_PATTERN,
    EMBEDDED_CODE,
    FLOAT_CODE,
    GRUPO_MAX_LEVEL,
    IGNORED_COLUMN_NOTES,
    IMPORT_JUSTIFICATION,
    IMPORT_MESSAGES,
    INSUMO_EDITABLE_COLUMN,
    QUANTITY_PLACES,
    SKU_EXAMPLE,
)
from app.core.clock import local_date
from app.core.config import get_settings
from app.models.ata import Ata
from app.models.insumo import GrupoMaterial, Insumo, ItemAta
from app.models.user import User
from app.repositories import insumo as repo
from app.repositories import item_ata as repo_item
from app.repositories import user as repo_user
from app.services import importacao
from app.services.atas import jsonable
from app.services.audit import Event, record
from app.services.errors import (
    DuplicateGroup,
    GrupoNotFound,
    ImportRejected,
    InsumoDuplicado,
    InsumoNotFound,
    InvalidData,
    InvalidDomsCode,
    InvalidSku,
    InvalidSubstitute,
    UsuarioNotFound,
)

Scope = frozenset[uuid.UUID] | None


@dataclass(frozen=True)
class InsumoView:
    """An insumo with its grupo path, its derived situação and its substitute."""

    insumo: Insumo
    grupo_path: Sequence[GrupoMaterial]
    status: str
    substitute: Insumo | None


@dataclass(frozen=True)
class InsumoDetail(InsumoView):
    """One insumo with the ATAs it is an item of."""

    atas: Sequence[tuple[ItemAta, Ata]]


@dataclass(frozen=True)
class GrupoNode:
    """One grupo of the tree, with its children."""

    grupo: GrupoMaterial
    children: Sequence[GrupoNode]


@dataclass(frozen=True)
class CatalogueReport:
    """What a catalogue import did, or would do with `dry_run` (AC-0003-06 to -08)."""

    created: int
    updated: int
    unchanged: int
    corrected_descriptions: int
    ignored_columns: tuple[str, ...]
    notes: tuple[str, ...]
    dry_run: bool


# ── Scope (RN07) ────────────────────────────────────────────────────────────


def scope_of(session: Session, user: User) -> Scope:
    """The grupos a caller may see, or None when nothing is hidden from it (AC-0003-29).

    Read on every request rather than carried in the token, so a gestor's change
    applies at once (AC-0003-30).
    """
    if user.role != "servidor":
        return None
    return frozenset(repo.descendants(session, repo.grupos_of_user(session, user.id)))


def visible(scope: Scope, insumo: Insumo) -> bool:
    """Whether a caller with this scope may see the insumo."""
    return scope is None or insumo.grupo_id in scope


def set_user_grupos(
    session: Session,
    *,
    actor: User,
    user_id: uuid.UUID,
    grupo_ids: Collection[uuid.UUID],
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> set[uuid.UUID]:
    """Replace the grupos a servidor owns (AC-0003-30).

    A gestor or an auditor is not scoped, so giving one grupos is refused rather
    than stored with no effect.
    """
    member = repo_user.by_id(session, user_id)
    if member is None:
        raise UsuarioNotFound()
    if member.role != "servidor":
        raise InvalidData({"grupo_ids": "Só um servidor tem grupos."})
    wanted = set(grupo_ids)
    unknown = [g for g in wanted if repo.grupo_by_id(session, g) is None]
    if unknown:
        raise InvalidData({"grupo_ids": "Grupo não encontrado."})
    previous = repo.grupos_of_user(session, user_id)
    if previous == wanted:
        return wanted
    repo.replace_grupos_of_user(session, user_id, wanted)
    _audit(
        session,
        "usuario",
        member.id,
        "usuario.grupos_alterados",
        actor,
        correlation_id,
        at,
        previous={"grupos": sorted(str(g) for g in previous)},
    )
    return wanted


# ── Grupos (AC-0003-09, -13) ────────────────────────────────────────────────


def grupo_tree(session: Session, scope: Scope) -> list[GrupoNode]:
    """The grupos as a forest; a servidor sees only its own and those below them."""
    grupos = [g for g in repo.all_grupos(session) if scope is None or g.id in scope]
    present = {g.id for g in grupos}
    children: dict[uuid.UUID | None, list[GrupoMaterial]] = {}
    for grupo in grupos:
        parent = grupo.parent_id if grupo.parent_id in present else None
        children.setdefault(parent, []).append(grupo)

    def build(parent: uuid.UUID | None) -> list[GrupoNode]:
        return [GrupoNode(g, build(g.id)) for g in children.get(parent, [])]

    return build(None)


def create_grupo(
    session: Session,
    *,
    actor: User,
    name: str,
    parent_id: uuid.UUID | None,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
    justification: str | None = None,
) -> GrupoMaterial:
    """Create a grupo at the level below its parent, at most the third (AC-0003-09)."""
    level = 1
    if parent_id is not None:
        parent = repo.grupo_by_id(session, parent_id)
        if parent is None:
            raise InvalidData({"parent_id": "Grupo não encontrado."})
        if parent.level >= GRUPO_MAX_LEVEL:
            raise InvalidData({"parent_id": "A classificação é o último nível."})
        level = parent.level + 1
    if repo.grupo_by_name(session, name, parent_id) is not None:
        raise DuplicateGroup()
    grupo = GrupoMaterial(name=name, level=level, parent_id=parent_id, criado_em=at)
    try:
        with session.begin_nested():
            repo.add_grupo(session, grupo)
    except IntegrityError as exc:
        raise DuplicateGroup() from exc
    _audit(
        session,
        "grupo_material",
        grupo.id,
        "grupo_material.criado",
        actor,
        correlation_id,
        at,
        previous=None,
        justification=justification,
    )
    return grupo


def rename_grupo(
    session: Session,
    *,
    actor: User,
    grupo_id: uuid.UUID,
    name: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> GrupoMaterial:
    """Rename a grupo; every insumo in it stays in it (AC-0003-13)."""
    grupo = repo.grupo_by_id(session, grupo_id)
    if grupo is None:
        raise GrupoNotFound()
    if grupo.name == name:
        return grupo
    other = repo.grupo_by_name(session, name, grupo.parent_id)
    if other is not None and other.id != grupo.id:
        raise DuplicateGroup()
    previous = {"nome": grupo.name}
    grupo.name = name
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise DuplicateGroup() from exc
    _audit(
        session,
        "grupo_material",
        grupo.id,
        "grupo_material.editado",
        actor,
        correlation_id,
        at,
        previous=previous,
    )
    return grupo


# ── The catalogue (AC-0003-01 to -05, -10 to -12) ───────────────────────────


def normalise_sku(raw: str) -> str:
    """Trim and uppercase a SKU, then refuse it when it misses the pattern (AC-0003-02)."""
    sku = raw.strip().upper()
    if not re.fullmatch(get_settings().sku_pattern, sku):
        raise InvalidSku(SKU_EXAMPLE)
    return sku


def check_codigo_doms(raw: str | None) -> str | None:
    """A DOMS code is digits only; `2888.0` is refused, not trimmed (AC-0003-02)."""
    if raw is None or not raw.strip():
        return None
    code = raw.strip()
    if not DOMS_CODE_PATTERN.fullmatch(code):
        raise InvalidDomsCode()
    return code


def register(
    session: Session,
    *,
    actor: User,
    sku: str,
    description: str,
    unit: str,
    grupo_id: uuid.UUID,
    codigo_doms: str | None,
    external_code: str | None,
    reference_quantity: decimal.Decimal | None,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Insumo:
    """Register an insumo (AC-0003-01 to -03); a servidor only inside its grupos."""
    scope = scope_of(session, actor)
    normalised = normalise_sku(sku)
    code = check_codigo_doms(codigo_doms)
    _require_grupo(session, grupo_id, scope)
    _require_unique(session, scope, sku=normalised, codigo_doms=code, other_than=None)

    insumo = Insumo(
        sku=normalised,
        codigo_doms=code,
        external_code=(external_code or "").strip() or None,
        description=description,
        unit=unit,
        grupo_id=grupo_id,
        reference_quantity=reference_quantity,
        criado_em=at,
        atualizado_em=at,
    )
    try:
        # A savepoint, so losing a race on the SKU leaves the request's own
        # transaction usable for the error to be reported from.
        with session.begin_nested():
            repo.add_insumo(session, insumo)
    except IntegrityError as exc:
        raise InsumoDuplicado(None) from exc
    _audit(session, "insumo", insumo.id, "insumo.criado", actor, correlation_id, at, previous=None)
    return insumo


def edit(
    session: Session,
    *,
    actor: User,
    insumo_id: uuid.UUID,
    changes: dict[str, Any],
    at: datetime.datetime,
    correlation_id: uuid.UUID,
    justification: str | None = None,
) -> Insumo:
    """Correct an insumo's fields, never its SKU (AC-0003-11)."""
    scope = scope_of(session, actor)
    insumo = _lock_visible(session, insumo_id, scope)
    if "codigo_doms" in changes:
        changes["codigo_doms"] = check_codigo_doms(changes["codigo_doms"])
    if "external_code" in changes:
        changes["external_code"] = (changes["external_code"] or "").strip() or None
    effective = {key: value for key, value in changes.items() if getattr(insumo, key) != value}
    if not effective:
        return insumo
    if "grupo_id" in effective:
        _require_grupo(session, effective["grupo_id"], scope)
    if effective.get("codigo_doms") is not None:
        _require_unique(
            session, scope, sku=None, codigo_doms=effective["codigo_doms"], other_than=insumo.id
        )

    previous = {INSUMO_EDITABLE_COLUMN[key]: getattr(insumo, key) for key in effective}
    for key, value in effective.items():
        setattr(insumo, key, value)
    insumo.atualizado_em = at
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise InsumoDuplicado(None) from exc
    _audit(
        session,
        "insumo",
        insumo.id,
        "insumo.editado",
        actor,
        correlation_id,
        at,
        previous=previous,
        justification=justification,
    )
    return insumo


def change_sku(
    session: Session,
    *,
    actor: User,
    insumo_id: uuid.UUID,
    sku: str,
    justification: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Insumo:
    """Change a SKU, with a justification; links go by id, so none breaks (AC-0003-04)."""
    insumo = _lock_visible(session, insumo_id, None)
    normalised = normalise_sku(sku)
    if normalised == insumo.sku:
        return insumo
    _require_unique(session, None, sku=normalised, codigo_doms=None, other_than=insumo.id)
    previous = {"sku": insumo.sku}
    insumo.sku = normalised
    insumo.atualizado_em = at
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise InsumoDuplicado(None) from exc
    _audit(
        session,
        "insumo",
        insumo.id,
        "insumo.sku_alterado",
        actor,
        correlation_id,
        at,
        previous=previous,
        justification=justification,
    )
    return insumo


def discontinue(
    session: Session,
    *,
    actor: User,
    insumo_id: uuid.UUID,
    justification: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Insumo:
    """Discontinue an ativo insumo; every link to it stays as it is (AC-0003-14)."""
    insumo = _lock_visible(session, insumo_id, None)
    if status_of(insumo) != "ativo":
        raise InvalidData({"status": "Este insumo já está descontinuado."})
    insumo.discontinued_on = local_date(at)
    insumo.atualizado_em = at
    session.flush()
    _audit(
        session,
        "insumo",
        insumo.id,
        "insumo.descontinuado",
        actor,
        correlation_id,
        at,
        previous={"descontinuado_em": None},
        justification=justification,
    )
    return insumo


def substitute(
    session: Session,
    *,
    actor: User,
    insumo_id: uuid.UUID,
    substitute_id: uuid.UUID,
    justification: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Insumo:
    """Point an ativo insumo at the ativo one that replaces it (AC-0003-15).

    A link, never a rewrite: the old insumo keeps its SKU, its descrição and
    every link, so historical NEs keep showing it (OQ-23, RN14). Because the
    substitute must be ativo, a chain can grow but never loop.
    """
    insumo = _lock_visible(session, insumo_id, None)
    if status_of(insumo) != "ativo":
        raise InvalidData({"status": "Este insumo já está descontinuado."})
    target = repo.insumo_by_id(session, substitute_id)
    if target is None or target.id == insumo.id or status_of(target) != "ativo":
        raise InvalidSubstitute()
    insumo.substitute_id = target.id
    insumo.discontinued_on = local_date(at)
    insumo.atualizado_em = at
    session.flush()
    _audit(
        session,
        "insumo",
        insumo.id,
        "insumo.substituido",
        actor,
        correlation_id,
        at,
        previous={"substituido_por_id": None, "descontinuado_em": None, "substituto": target.sku},
        justification=justification,
    )
    return insumo


def reactivate(
    session: Session,
    *,
    actor: User,
    insumo_id: uuid.UUID,
    justification: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Insumo:
    """Undo a discontinuation or a substitution made by mistake (AC-0003-16)."""
    insumo = _lock_visible(session, insumo_id, None)
    if status_of(insumo) == "ativo":
        raise InvalidData({"status": "Este insumo já está ativo."})
    previous = {
        "descontinuado_em": insumo.discontinued_on,
        "substituido_por_id": insumo.substitute_id,
    }
    insumo.discontinued_on = None
    insumo.substitute_id = None
    insumo.atualizado_em = at
    session.flush()
    _audit(
        session,
        "insumo",
        insumo.id,
        "insumo.reativado",
        actor,
        correlation_id,
        at,
        previous=previous,
        justification=justification,
    )
    return insumo


def status_of(insumo: Insumo) -> str:
    """`ativo`, `descontinuado` or `substituido`, derived (AC-0003-12)."""
    if insumo.substitute_id is not None:
        return "substituido"
    if insumo.discontinued_on is not None:
        return "descontinuado"
    return "ativo"


def get(session: Session, insumo_id: uuid.UUID, *, actor: User) -> InsumoDetail:
    """One insumo, with the ATAs it is an item of; 404 outside the caller's scope."""
    scope = scope_of(session, actor)
    insumo = repo.insumo_by_id(session, insumo_id)
    if insumo is None or not visible(scope, insumo):
        raise InsumoNotFound()
    view = views(session, [insumo])[0]
    return InsumoDetail(
        insumo=view.insumo,
        grupo_path=view.grupo_path,
        status=view.status,
        substitute=view.substitute,
        atas=repo_item.atas_of_insumo(session, insumo.id),
    )


def list_insumos(
    session: Session,
    *,
    actor: User,
    page: int,
    size: int,
    query: str | None,
    grupo_id: uuid.UUID | None,
    status: str | None,
) -> tuple[list[InsumoView], int]:
    """A page of the catalogue, searched and filtered, inside the caller's scope (AC-0003-12)."""
    scope = scope_of(session, actor)
    allowed: set[uuid.UUID] | None = None if scope is None else set(scope)
    if grupo_id is not None:
        below = repo.descendants(session, [grupo_id])
        allowed = below if allowed is None else allowed & below
    discontinued: bool | None = None
    substituted: bool | None = None
    if status == "ativo":
        discontinued, substituted = False, False
    elif status == "descontinuado":
        discontinued, substituted = True, False
    elif status == "substituido":
        substituted = True
    rows, total = repo.list_insumos(
        session,
        page=page,
        size=size,
        query=query.strip() if query else None,
        grupo_ids=allowed,
        discontinued=discontinued,
        substituted=substituted,
    )
    return views(session, rows), total


def views(session: Session, insumos: Sequence[Insumo]) -> list[InsumoView]:
    """Each insumo with its grupo path, situação and substitute."""
    grupos = {g.id: g for g in repo.all_grupos(session)}
    substitutes = repo.insumos_by_id(
        session, {i.substitute_id for i in insumos if i.substitute_id is not None}
    )
    return [
        InsumoView(
            insumo=insumo,
            grupo_path=_path(grupos, insumo.grupo_id),
            status=status_of(insumo),
            substitute=substitutes.get(insumo.substitute_id) if insumo.substitute_id else None,
        )
        for insumo in insumos
    ]


# ── The catalogue file (AC-0003-06 to -08, -18, -19) ────────────────────────


@dataclass(frozen=True)
class _CatalogueRow:
    line: int
    sku: str
    description: str
    unit: str
    path: tuple[str, ...]
    codigo_doms: str | None
    external_code: str | None
    reference_quantity: decimal.Decimal | None
    corrected: bool


def import_catalogue(
    session: Session,
    *,
    actor: User,
    content: bytes,
    dry_run: bool,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> CatalogueReport:
    """Create or update insumos by SKU from a file, all or nothing (AC-0003-06 to -08).

    With `dry_run` the same work is done inside a savepoint that is rolled back,
    so the report is exactly what the import would do.
    """
    sheet = importacao.read(content, required=CATALOGUE_REQUIRED, optional=CATALOGUE_OPTIONAL)
    report = importacao.Report()
    rows = _parse_catalogue(sheet, report)

    by_sku = repo.insumos_by_sku(session, {row.sku for row in rows})
    by_doms = repo.insumos_by_codigo_doms(
        session, {row.codigo_doms for row in rows if row.codigo_doms}
    )
    for row in rows:
        owner = by_doms.get(row.codigo_doms) if row.codigo_doms else None
        if owner is not None and owner.sku != row.sku:
            report.error(
                row.line, "codigo_doms", IMPORT_MESSAGES["doms_in_use"].format(sku=owner.sku)
            )
    report.raise_if_any()

    created = updated = unchanged = 0
    savepoint = session.begin_nested()
    try:
        grupos: dict[tuple[str, ...], uuid.UUID] = {}
        for row in rows:
            grupo_id = _grupo_for_path(session, actor, row.path, grupos, at, correlation_id)
            existing = by_sku.get(row.sku)
            if existing is None:
                insumo = repo.add_insumo(
                    session,
                    Insumo(
                        sku=row.sku,
                        codigo_doms=row.codigo_doms,
                        external_code=row.external_code,
                        description=row.description,
                        unit=row.unit,
                        grupo_id=grupo_id,
                        reference_quantity=row.reference_quantity,
                        criado_em=at,
                        atualizado_em=at,
                    ),
                )
                _audit(
                    session,
                    "insumo",
                    insumo.id,
                    "insumo.criado",
                    actor,
                    correlation_id,
                    at,
                    previous=None,
                    justification=IMPORT_JUSTIFICATION,
                )
                created += 1
                continue
            # An empty optional cell keeps what is stored, so a file with fewer
            # columns does not erase what another file filled in (AC-0003-08).
            wanted: dict[str, Any] = {
                "description": row.description,
                "unit": row.unit,
                "grupo_id": grupo_id,
            }
            if row.codigo_doms is not None:
                wanted["codigo_doms"] = row.codigo_doms
            if row.external_code is not None:
                wanted["external_code"] = row.external_code
            if row.reference_quantity is not None:
                wanted["reference_quantity"] = row.reference_quantity
            changes = {k: v for k, v in wanted.items() if getattr(existing, k) != v}
            if not changes:
                unchanged += 1
                continue
            previous = {INSUMO_EDITABLE_COLUMN[k]: getattr(existing, k) for k in changes}
            for key, value in changes.items():
                setattr(existing, key, value)
            existing.atualizado_em = at
            session.flush()
            _audit(
                session,
                "insumo",
                existing.id,
                "insumo.editado",
                actor,
                correlation_id,
                at,
                previous=previous,
                justification=IMPORT_JUSTIFICATION,
            )
            updated += 1
    except IntegrityError as exc:
        savepoint.rollback()
        # Two lines swapping DOMS codes collide on the unique index mid-file.
        raise ImportRejected(
            [{"line": 1, "field": "codigo_doms", "message": "Códigos DOMS trocados entre linhas."}]
        ) from exc
    if dry_run:
        savepoint.rollback()
    else:
        savepoint.commit()

    notes = tuple(
        IGNORED_COLUMN_NOTES[column]
        for column in sheet.unknown_columns
        if column in IGNORED_COLUMN_NOTES
    )
    return CatalogueReport(
        created=created,
        updated=updated,
        unchanged=unchanged,
        corrected_descriptions=sum(1 for row in rows if row.corrected),
        ignored_columns=sheet.unknown_columns,
        notes=notes,
        dry_run=dry_run,
    )


def _parse_catalogue(sheet: importacao.Sheet, report: importacao.Report) -> list[_CatalogueRow]:
    rows: list[_CatalogueRow] = []
    first_sku: dict[str, int] = {}
    first_doms: dict[str, int] = {}
    for line, cells in sheet.lines:
        before = len(report.rows)
        for column in CATALOGUE_REQUIRED:
            if not cells.get(column):
                report.error(line, column, IMPORT_MESSAGES["required"])

        sku = cells.get("sku", "").upper()
        if sku and not re.fullmatch(get_settings().sku_pattern, sku):
            report.error(line, "sku", IMPORT_MESSAGES["sku"])

        codigo_doms = cells.get("codigo_doms") or None
        if codigo_doms is not None and not DOMS_CODE_PATTERN.fullmatch(codigo_doms):
            key = "float_code" if FLOAT_CODE.fullmatch(codigo_doms) else "doms"
            report.error(line, "codigo_doms", IMPORT_MESSAGES[key])
        external_code = cells.get("codigo_externo") or None
        if external_code is not None and FLOAT_CODE.fullmatch(external_code):
            report.error(line, "codigo_externo", IMPORT_MESSAGES["float_code"])

        # `26829 - CLOREXIDINA 2% - 1 L`: two facts in one cell; the code is
        # lifted out, and refused when it contradicts the code column (AC-0003-19).
        description = cells.get("descricao", "")
        corrected = False
        embedded = EMBEDDED_CODE.fullmatch(description)
        if embedded:
            code, rest = embedded.groups()
            if codigo_doms is None:
                codigo_doms = code
            elif codigo_doms != code:
                report.error(line, "descricao", IMPORT_MESSAGES["embedded_mismatch"])
            description, corrected = rest.strip(), True

        subgrupo = cells.get("subgrupo", "")
        classificacao = cells.get("classificacao", "")
        if classificacao and not subgrupo:
            report.error(line, "classificacao", IMPORT_MESSAGES["classificacao_without_subgrupo"])
        path = tuple(name for name in (cells.get("grupo", ""), subgrupo, classificacao) if name)

        reference: decimal.Decimal | None = None
        if cells.get("quantidade_referencia"):
            try:
                reference = importacao.number(
                    cells["quantidade_referencia"],
                    separator=sheet.separator,
                    places=QUANTITY_PLACES,
                    positive=False,
                )
            except importacao.CellError as exc:
                report.error(line, "quantidade_referencia", str(exc))

        if sku in first_sku:
            report.error(line, "sku", IMPORT_MESSAGES["duplicate_sku"].format(other=first_sku[sku]))
        elif sku:
            first_sku[sku] = line
        if codigo_doms and codigo_doms in first_doms:
            report.error(
                line,
                "codigo_doms",
                IMPORT_MESSAGES["duplicate_doms"].format(other=first_doms[codigo_doms]),
            )
        elif codigo_doms:
            first_doms[codigo_doms] = line

        if len(report.rows) == before:
            rows.append(
                _CatalogueRow(
                    line=line,
                    sku=sku,
                    description=description,
                    unit=cells["unidade"],
                    path=path,
                    codigo_doms=codigo_doms,
                    external_code=external_code,
                    reference_quantity=reference,
                    corrected=corrected,
                )
            )
    return rows


def _grupo_for_path(
    session: Session,
    actor: User,
    path: tuple[str, ...],
    cache: dict[tuple[str, ...], uuid.UUID],
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> uuid.UUID:
    """Find each level of a grupo path by name under its parent, or create it."""
    parent: uuid.UUID | None = None
    for depth in range(1, len(path) + 1):
        key = tuple(name.lower() for name in path[:depth])
        if key in cache:
            parent = cache[key]
            continue
        name = path[depth - 1]
        found = repo.grupo_by_name(session, name, parent)
        if found is None:
            found = create_grupo(
                session,
                actor=actor,
                name=name,
                parent_id=parent,
                at=at,
                correlation_id=correlation_id,
                justification=IMPORT_JUSTIFICATION,
            )
        cache[key] = parent = found.id
    assert parent is not None  # `grupo` is a required column
    return parent


# ── Helpers ─────────────────────────────────────────────────────────────────


def _lock_visible(session: Session, insumo_id: uuid.UUID, scope: Scope) -> Insumo:
    insumo = repo.insumo_by_id_for_update(session, insumo_id)
    if insumo is None or not visible(scope, insumo):
        raise InsumoNotFound()
    return insumo


def _require_grupo(session: Session, grupo_id: uuid.UUID, scope: Scope) -> None:
    if repo.grupo_by_id(session, grupo_id) is None:
        raise InvalidData({"grupo_id": "Grupo não encontrado."})
    if scope is not None and grupo_id not in scope:
        raise InvalidData({"grupo_id": "Escolha um grupo da sua área."})


def _require_unique(
    session: Session,
    scope: Scope,
    *,
    sku: str | None,
    codigo_doms: str | None,
    other_than: uuid.UUID | None,
) -> None:
    for existing in (
        repo.insumo_by_sku(session, sku) if sku else None,
        repo.insumo_by_codigo_doms(session, codigo_doms) if codigo_doms else None,
    ):
        if existing is not None and existing.id != other_than:
            named = f"{existing.sku} {existing.description}" if visible(scope, existing) else None
            raise InsumoDuplicado(named)


def _path(grupos: dict[uuid.UUID, GrupoMaterial], grupo_id: uuid.UUID) -> list[GrupoMaterial]:
    path: list[GrupoMaterial] = []
    current: uuid.UUID | None = grupo_id
    while current is not None and current in grupos:
        path.append(grupos[current])
        current = grupos[current].parent_id
    return list(reversed(path))


def _audit(
    session: Session,
    entidade_tipo: str,
    entidade_id: uuid.UUID,
    acao: str,
    actor: User,
    correlation_id: uuid.UUID,
    at: datetime.datetime,
    *,
    previous: dict[str, Any] | None,
    justification: str | None = None,
) -> None:
    record(
        session,
        Event(
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            acao=acao,
            user_id=actor.id,
            dados_anteriores=jsonable(previous) if previous is not None else None,
            justificativa=justification,
        ),
        correlation_id=correlation_id,
        at=at,
    )
