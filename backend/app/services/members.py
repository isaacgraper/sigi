"""Member management (SPEC-0001 §4.2 — AC-0001-10, -11, -25, -26, -28).

This is the module that creates accounts. There is no self-registration and no
just-in-time provisioning from the identity provider (AC-0001-21), so every
usuario in the system passes through `invite` — which also means a defect here
is a defect in who can enter the system at all.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.passwords import hash_password
from app.models.user import User
from app.repositories import user as repo
from app.services import credentials
from app.services.audit import Event, record
from app.services.errors import (
    EmailAlreadyRegistered,
    NonInstitutionalDomain,
    UsuarioNotFound,
)


def invite(
    session: Session,
    *,
    actor: User,
    email: str,
    role: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> tuple[User, str]:
    """Create a `pendente` account and issue its activation link (AC-0001-10).

    Returns the usuario and the link. The link exists in memory for the length
    of this response and nowhere else, because only its HMAC is stored, so the
    caller must hand it to the gestor and must not log it.
    """
    cfg = get_settings()
    address = email.strip().lower()
    _require_institutional_domain(address, cfg.dominios_institucionais)

    if repo.by_email(session, address) is not None:
        # In any status, `desativado` included. A second account for one person
        # splits their audit trail in two, and neither half answers "what did
        # this person do" (AC-0001-28).
        raise EmailAlreadyRegistered()

    user = repo.create(session, email=address, role=role)
    grant = credentials.issue(
        session,
        usuario_id=user.id,
        tipo=credentials.INVITE,
        at=at,
        criado_por=actor.id,
    )
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="usuario.convidado",
            usuario_id=actor.id,
            # The perfil granted, never the token: this table can never be
            # corrected, and `lgpd.md` promises it carries no credential.
            dados_anteriores={"perfil": role},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user, grant.link("/convite")


def activate(
    session: Session,
    *,
    token: str,
    password: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> User:
    """Redeem an invitation and set the credential (AC-0001-11, -25, -26).

    Order matters and is the criterion: the password is validated **before** the
    grant is spent, so a password that fails the policy leaves the invitation
    usable. A typo must not burn it and force the gestor to issue another.
    """
    row = credentials.redeem(session, value=token, tipo=credentials.INVITE, at=at)
    credentials.require_strong_password(password)

    user = repo.by_id(session, row.usuario_id)
    if user is None:  # pragma: no cover - the foreign key makes this unreachable
        raise UsuarioNotFound()

    user.senha_hash = hash_password(password)
    user.status = "ativo"
    credentials.consume(session, row, at=at)
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="usuario.ativado",
            usuario_id=user.id,
            dados_anteriores={"status": "pendente"},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user


def _require_institutional_domain(email: str, allowed: list[str]) -> None:
    _, _, domain = email.rpartition("@")
    accepted = bool(domain) and any(
        domain == d.lower() or domain.endswith(f".{d.lower()}") for d in allowed
    )
    if not accepted:
        raise NonInstitutionalDomain(allowed)
