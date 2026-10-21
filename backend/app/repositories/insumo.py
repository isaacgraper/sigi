"""Data access for `grupo_material`, `insumo` and `usuario_grupo_material`.

No business rule lives here (`CLAUDE.md`): the service decides what a scope or a
situação means and passes plain ids and flags in.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.insumo import GrupoMaterial, Insumo, UsuarioGrupoMaterial

# ── Grupos ──────────────────────────────────────────────────────────────────


def all_grupos(session: Session) -> Sequence[GrupoMaterial]:
    """Every grupo, ordered by level and name. The table holds hundreds, not millions."""
    return session.scalars(
        select(GrupoMaterial).order_by(GrupoMaterial.level, func.lower(GrupoMaterial.name))
    ).all()


def grupo_by_id(session: Session, grupo_id: uuid.UUID) -> GrupoMaterial | None:
    """Find a grupo by id, or None."""
    return session.get(GrupoMaterial, grupo_id)


def grupo_by_name(session: Session, name: str, parent_id: uuid.UUID | None) -> GrupoMaterial | None:
    """Find a grupo by name under a parent, ignoring case, or None."""
    parent = (
        GrupoMaterial.parent_id.is_(None)
        if parent_id is None
        else GrupoMaterial.parent_id == parent_id
    )
    return session.scalars(
        select(GrupoMaterial).where(func.lower(GrupoMaterial.name) == name.lower(), parent)
    ).one_or_none()


def add_grupo(session: Session, grupo: GrupoMaterial) -> GrupoMaterial:
    """Insert a grupo and flush it."""
    session.add(grupo)
    session.flush()
    return grupo


def descendants(session: Session, roots: Collection[uuid.UUID]) -> set[uuid.UUID]:
    """The ids of the given grupos and of every grupo below them."""
    if not roots:
        return set()
    tree = (
        select(GrupoMaterial.id)
        .where(GrupoMaterial.id.in_(list(roots)))
        .cte("arvore", recursive=True)
    )
    tree = tree.union_all(select(GrupoMaterial.id).where(GrupoMaterial.parent_id == tree.c.id))
    return set(session.scalars(select(tree.c.id)).all())


# ── Insumos ─────────────────────────────────────────────────────────────────


def insumo_by_id(session: Session, insumo_id: uuid.UUID) -> Insumo | None:
    """Find an insumo by id, or None."""
    return session.get(Insumo, insumo_id)


def insumo_by_id_for_update(session: Session, insumo_id: uuid.UUID) -> Insumo | None:
    """Find an insumo and lock its row until the transaction ends."""
    return session.scalars(
        select(Insumo).where(Insumo.id == insumo_id).with_for_update()
    ).one_or_none()


def insumo_by_sku(session: Session, sku: str) -> Insumo | None:
    """Find an insumo by its SKU, or None."""
    return session.scalars(select(Insumo).where(Insumo.sku == sku)).one_or_none()


def insumo_by_codigo_doms(session: Session, codigo_doms: str) -> Insumo | None:
    """Find an insumo by its DOMS code, or None."""
    return session.scalars(select(Insumo).where(Insumo.codigo_doms == codigo_doms)).one_or_none()


def insumos_by_sku(session: Session, skus: Collection[str]) -> dict[str, Insumo]:
    """The insumos with these SKUs, keyed by SKU."""
    if not skus:
        return {}
    rows = session.scalars(select(Insumo).where(Insumo.sku.in_(list(skus)))).all()
    return {row.sku: row for row in rows}


def insumos_by_codigo_doms(session: Session, codes: Collection[str]) -> dict[str, Insumo]:
    """The insumos with these DOMS codes, keyed by code."""
    if not codes:
        return {}
    rows = session.scalars(select(Insumo).where(Insumo.codigo_doms.in_(list(codes)))).all()
    return {row.codigo_doms: row for row in rows if row.codigo_doms is not None}


def insumos_by_id(session: Session, ids: Collection[uuid.UUID]) -> dict[uuid.UUID, Insumo]:
    """The insumos with these ids, keyed by id."""
    if not ids:
        return {}
    rows = session.scalars(select(Insumo).where(Insumo.id.in_(list(ids)))).all()
    return {row.id: row for row in rows}


def add_insumo(session: Session, insumo: Insumo) -> Insumo:
    """Insert an insumo and flush it."""
    session.add(insumo)
    session.flush()
    return insumo


def list_insumos(
    session: Session,
    *,
    page: int,
    size: int,
    query: str | None,
    grupo_ids: Collection[uuid.UUID] | None,
    discontinued: bool | None,
    substituted: bool | None,
) -> tuple[Sequence[Insumo], int]:
    """One page of insumos ordered by SKU, and the total that matches.

    `grupo_ids` None means no restriction by grupo; an empty collection matches
    nothing.
    """
    conditions = []
    if query:
        pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions.append(
            or_(
                Insumo.sku.ilike(pattern, escape="\\"),
                Insumo.codigo_doms.ilike(pattern, escape="\\"),
                Insumo.description.ilike(pattern, escape="\\"),
            )
        )
    if grupo_ids is not None:
        conditions.append(Insumo.grupo_id.in_(list(grupo_ids)))
    if discontinued is not None:
        column = Insumo.discontinued_on
        conditions.append(column.is_not(None) if discontinued else column.is_(None))
    if substituted is not None:
        conditions.append(
            Insumo.substitute_id.is_not(None) if substituted else Insumo.substitute_id.is_(None)
        )
    total = session.scalar(select(func.count()).select_from(Insumo).where(*conditions)) or 0
    rows = session.scalars(
        select(Insumo).where(*conditions).order_by(Insumo.sku).offset((page - 1) * size).limit(size)
    ).all()
    return rows, int(total)


# ── A servidor's grupos (RN07) ──────────────────────────────────────────────


def grupos_of_user(session: Session, user_id: uuid.UUID) -> set[uuid.UUID]:
    """The grupos a member owns."""
    return set(
        session.scalars(
            select(UsuarioGrupoMaterial.grupo_id).where(UsuarioGrupoMaterial.usuario_id == user_id)
        ).all()
    )


def replace_grupos_of_user(
    session: Session, user_id: uuid.UUID, grupo_ids: Collection[uuid.UUID]
) -> None:
    """Replace the set of grupos a member owns."""
    session.execute(delete(UsuarioGrupoMaterial).where(UsuarioGrupoMaterial.usuario_id == user_id))
    session.add_all(UsuarioGrupoMaterial(usuario_id=user_id, grupo_id=g) for g in grupo_ids)
    session.flush()
