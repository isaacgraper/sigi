"""A fictitious sample for a development install (`python -m app.cli seed-demo`).

Everything goes through the same services the API calls, as the seeded gestor,
so every row has its audit row and every rule holds: nothing here could not have
been typed on the screens. Runs once; a second run finds the marker ATA and
stops. Refused outside development, like the admin's seed (AC-0001-40).
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.constants.demo import (
    DEMO_ATAS,
    DEMO_DISCONTINUED,
    DEMO_FORNECEDORES,
    DEMO_GRUPOS,
    DEMO_INSUMOS,
    DEMO_ITEMS,
    DEMO_JUSTIFICATION,
    DEMO_MARKER_ATA,
    DEMO_MEMBERS,
    DEMO_QUANTITY_ADITIVOS,
    DEMO_REAJUSTES,
    DEMO_SERVIDOR_GRUPOS,
    DEMO_SUBSTITUTIONS,
    DEMO_VALUE_ADITIVOS,
)
from app.constants.members import DEV_ADMIN_EMAIL
from app.core.clock import local_date
from app.core.config import get_settings
from app.core.passwords import hash_password
from app.models.user import User
from app.repositories import ata as repo_ata
from app.repositories import user as repo_user
from app.services import atas, insumos, itens_ata, members
from app.services.atas import FornecedorInput
from app.services.audit import Event, record
from app.services.errors import DevelopmentOnly


@dataclass
class DemoReport:
    """What the seed created, for the command line to print."""

    loaded: bool
    members: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


def seed_demo(session: Session, *, at: datetime.datetime, correlation_id: uuid.UUID) -> DemoReport:
    """Load the sample once; report `loaded=False` when it is already there."""
    if get_settings().app_env != "development":
        raise DevelopmentOnly()
    if repo_ata.by_number(session, DEMO_MARKER_ATA) is not None:
        return DemoReport(loaded=False)

    gestor = repo_user.by_email(session, DEV_ADMIN_EMAIL) or members.seed_dev_admin(
        session, at=at, correlation_id=correlation_id
    )
    assert gestor is not None  # seed_dev_admin returns None only when the gestor exists
    today = local_date(at)
    report = DemoReport(loaded=True)

    people = {m["perfil"]: _member(session, m, at, correlation_id) for m in DEMO_MEMBERS}
    report.members = [m["email"] for m in DEMO_MEMBERS]

    grupos: dict[tuple[str, ...], uuid.UUID] = {}
    for root, subs in DEMO_GRUPOS.items():
        grupos[(root,)] = insumos.create_grupo(
            session, name=root, parent_id=None, actor=gestor, at=at, correlation_id=correlation_id
        ).id
        for sub, leaves in subs.items():
            grupos[(root, sub)] = insumos.create_grupo(
                session,
                name=sub,
                parent_id=grupos[(root,)],
                actor=gestor,
                at=at,
                correlation_id=correlation_id,
            ).id
            for leaf in leaves:
                grupos[(root, sub, leaf)] = insumos.create_grupo(
                    session,
                    name=leaf,
                    parent_id=grupos[(root, sub)],
                    actor=gestor,
                    at=at,
                    correlation_id=correlation_id,
                ).id
    insumos.set_user_grupos(
        session,
        user_id=people["servidor"].id,
        grupo_ids=[grupos[(name,)] for name in DEMO_SERVIDOR_GRUPOS],
        actor=gestor,
        at=at,
        correlation_id=correlation_id,
    )

    catalogue: dict[str, uuid.UUID] = {}
    for sku, description, unit, path, codigo_doms in DEMO_INSUMOS:
        catalogue[sku] = insumos.register(
            session,
            sku=sku,
            description=description,
            unit=unit,
            grupo_id=grupos[path],
            codigo_doms=codigo_doms,
            external_code=None,
            reference_quantity=None,
            actor=gestor,
            at=at,
            correlation_id=correlation_id,
        ).id

    numbers: dict[str, uuid.UUID] = {}
    for number, subject, supplier, start, end, total, budget, _ in DEMO_ATAS:
        cnpj, legal_name = DEMO_FORNECEDORES[supplier]
        numbers[number] = atas.register(
            session,
            number=number,
            subject=subject,
            organ="Secretaria de Estado da Saúde (fictícia)",
            fornecedor=FornecedorInput(cnpj=cnpj, legal_name=legal_name),
            issued_on=today + datetime.timedelta(days=start),
            vigencia_inicio=today + datetime.timedelta(days=start),
            vigencia_fim=today + datetime.timedelta(days=end),
            total_value=decimal.Decimal(total),
            budget_date=today + datetime.timedelta(days=budget),
            actor=gestor,
            at=at,
            correlation_id=correlation_id,
        ).id

    item_ids: dict[tuple[str, str], uuid.UUID] = {}
    for number, sku, item_number, quantity, unit_price, own in DEMO_ITEMS:
        fornecedor = None
        if own is not None:
            cnpj, legal_name = DEMO_FORNECEDORES[own]
            fornecedor = FornecedorInput(cnpj=cnpj, legal_name=legal_name)
        item_ids[(number, sku)] = itens_ata.add_item(
            session,
            ata_id=numbers[number],
            insumo_id=catalogue[sku],
            quantity=decimal.Decimal(quantity),
            unit_price=decimal.Decimal(unit_price),
            item_number=item_number,
            fornecedor=fornecedor,
            actor=gestor,
            at=at,
            correlation_id=correlation_id,
        ).id

    for number, sku, quantity in DEMO_QUANTITY_ADITIVOS:
        itens_ata.add_quantity_aditivo(
            session,
            ata_id=numbers[number],
            item_id=item_ids[(number, sku)],
            quantity=decimal.Decimal(quantity),
            justification=DEMO_JUSTIFICATION,
            actor=gestor,
            at=at,
            correlation_id=correlation_id,
        )
    for number, value in DEMO_VALUE_ADITIVOS:
        atas.add_aditivo(
            session,
            ata_id=numbers[number],
            kind="valor",
            valor_acrescimo=decimal.Decimal(value),
            nova_vigencia_fim=None,
            justification=DEMO_JUSTIFICATION,
            actor=gestor,
            at=at,
            correlation_id=correlation_id,
        )
    for number, processo, requested in DEMO_REAJUSTES:
        atas.add_reajuste(
            session,
            ata_id=numbers[number],
            processo=processo,
            requested_on=today + datetime.timedelta(days=requested),
            actor=gestor,
            at=at,
            correlation_id=correlation_id,
        )

    # After the items, as on the screens: an ATA takes items while it runs.
    for number, *_, move in DEMO_ATAS:
        if move is not None:
            atas.move(
                session,
                ata_id=numbers[number],
                move_name=move,
                justification=DEMO_JUSTIFICATION,
                actor=gestor,
                at=at,
                correlation_id=correlation_id,
            )
    for old, new in DEMO_SUBSTITUTIONS:
        insumos.substitute(
            session,
            insumo_id=catalogue[old],
            substitute_id=catalogue[new],
            justification=DEMO_JUSTIFICATION,
            actor=gestor,
            at=at,
            correlation_id=correlation_id,
        )
    for sku in DEMO_DISCONTINUED:
        insumos.discontinue(
            session,
            insumo_id=catalogue[sku],
            justification=DEMO_JUSTIFICATION,
            actor=gestor,
            at=at,
            correlation_id=correlation_id,
        )

    report.counts = {
        "grupos": len(grupos),
        "insumos": len(catalogue),
        "atas": len(numbers),
        "itens": len(item_ids),
    }
    return report


def _member(
    session: Session, data: dict[str, str], at: datetime.datetime, correlation_id: uuid.UUID
) -> User:
    """An active member with a known password, or the one already there."""
    existing = repo_user.by_email(session, data["email"])
    if existing is not None:
        return existing
    user = repo_user.create(
        session,
        email=data["email"],
        role=data["perfil"],
        nome=data["nome"],
        registro_funcional=data["registro"],
    )
    # The password policy is skipped on purpose, as for the admin's seed: these
    # are development credentials, and this function refuses to run elsewhere.
    user.senha_hash = hash_password(data["password"])
    user.status = "ativo"
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="usuario.semente_demonstracao",
            user_id=None,
            dados_anteriores={"perfil": data["perfil"], "mecanismo": "semente_desenvolvimento"},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user
