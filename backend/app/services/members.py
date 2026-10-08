"""Member management (SPEC-0001 §4.2 — AC-0001-10 to -14, -25, -26, -28, -29, -44 to -46).

This is the module that creates accounts. There is no self-registration and no
just-in-time provisioning from the identity provider (AC-0001-21), so every
usuario in the system passes through `invite` — which also means a defect here
is a defect in who can enter the system at all.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Sequence

from psycopg import errors as pgerrors
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.passwords import hash_password
from app.models.user import User
from app.repositories import session as repo_session
from app.repositories import user as repo
from app.services import credentials
from app.services.audit import Event, record
from app.services.errors import (
    DevelopmentOnly,
    EmailAlreadyRegistered,
    GestorAlreadyExists,
    LastGestor,
    NonInstitutionalDomain,
    NotBlocked,
    NotPending,
    ResetAlreadyUsed,
    ResetExpired,
    UsuarioNotFound,
)

# PostgreSQL raises this when the last-gestor trigger's `FOR UPDATE` deadlocks
# against a concurrent removal. Measured over 40 runs of the AC-0001-29 race:
# exactly one deactivation always succeeds, and the loser sees a deadlock 39
# times and the trigger's own SI005 once. Both mean the same thing to the
# caller, so both become 409.
SQLSTATE_DEADLOCK = "40P01"
SQLSTATE_LAST_GESTOR = "SI005"

# `ck_sessao_motivo_valor` fixes the vocabulary of `sessao.revogado_motivo`,
# and it is not the vocabulary of `usuario.status`. Two languages: one
# describes the account, the other why the session ended.
REVOCATION_REASON = {"bloqueado": "bloqueio", "desativado": "desativacao"}


def invite(
    session: Session,
    *,
    actor: User,
    email: str,
    role: str,
    name: str,
    registration: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> tuple[User, str]:
    """Create a `pendente` account and issue its activation link (AC-0001-10, -45).

    Returns the usuario and the link. The link exists in memory for the length
    of this response and nowhere else, because only its HMAC is stored, so the
    caller must hand it to the gestor and must not log it.
    """
    cfg = get_settings()
    address = email.strip().lower()
    _require_institutional_domain(address, cfg.institutional_domains)

    if repo.by_email(session, address) is not None:
        # In any status, `desativado` included. A second account for one person
        # splits their audit trail in two, and neither half answers "what did
        # this person do" (AC-0001-28).
        raise EmailAlreadyRegistered()

    user = repo.create(
        session,
        email=address,
        role=role,
        nome=name.strip(),
        registro_funcional=registration.strip(),
    )
    grant = credentials.issue(
        session,
        user_id=user.id,
        kind=credentials.INVITE,
        at=at,
        created_by=actor.id,
    )
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="usuario.convidado",
            user_id=actor.id,
            # The perfil granted, never the token, the name or the registration:
            # this table can never be corrected, and `lgpd.md` promises it carries
            # neither a credential nor personal data (AC-0001-45).
            dados_anteriores={"perfil": role},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user, grant.link("/invite")


def reissue_invite(
    session: Session,
    *,
    actor: User,
    user_id: uuid.UUID,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> tuple[User, str]:
    """Issue a new activation link for a pending account (AC-0001-46).

    The link of AC-0001-10 is shown once, so one that was lost or left to expire
    had no replacement, and the address could never join: re-inviting it is
    refused (AC-0001-28). `credentials.issue` cancels the earlier grant, so at
    most one link is live and the old one answers `INVITE_EXPIRED`.
    """
    user = repo.by_id(session, user_id)
    if user is None:
        raise UsuarioNotFound()
    if user.status != "pendente":
        raise NotPending()

    grant = credentials.issue(
        session,
        user_id=user.id,
        kind=credentials.INVITE,
        at=at,
        created_by=actor.id,
    )
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="usuario.convite_reemitido",
            user_id=actor.id,
            # The perfil, never the token, as for the first invitation.
            dados_anteriores={"perfil": user.role},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user, grant.link("/invite")


def bootstrap_gestor(
    session: Session,
    *,
    email: str,
    password: str | None,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> User:
    """Create the first gestor, from the command line (AC-0001-34, -35, -36).

    Every other account comes from an invitation, which needs a gestor to issue
    it, so this is the one account with no actor. It is created `ativo` rather
    than invited, because an invitation must name who issued it (the
    `ck_token_convite_tem_autor` constraint) and nobody did. `password` is None
    for an install that logs in only through OIDC; the first institutional
    login then binds the account by e-mail (AC-0001-21).
    """
    cfg = get_settings()
    address = email.strip().lower()
    _require_institutional_domain(address, cfg.institutional_domains)
    if password is not None:
        credentials.require_strong_password(password)

    # The same lock the last-gestor guard takes: two operators racing must not
    # both see "no gestor" and each create one.
    repo.lock_gestores(session)
    if repo.count_active_gestores(session) > 0:
        raise GestorAlreadyExists()
    if repo.by_email(session, address) is not None:
        raise EmailAlreadyRegistered()

    user = repo.create(session, email=address, role="gestor")
    if password is not None:
        user.senha_hash = hash_password(password)
    user.status = "ativo"
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="usuario.gestor_inicial",
            user_id=None,
            dados_anteriores={
                "perfil": "gestor",
                "mecanismo": "local" if password is not None else "oidc",
            },
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user


DEV_ADMIN_EMAIL = "admin@sc.gov.br"
DEV_ADMIN_PASSWORD = "admin"  # noqa: S105 - a development credential, refused elsewhere


def seed_dev_admin(
    session: Session,
    *,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> User | None:
    """Create the development gestor, once (AC-0001-39, -40).

    Skips the password policy on purpose, which is exactly why it refuses to
    run anywhere but development: a shared, known credential is the first
    thing an attacker tries. Returns None when the account already exists.
    """
    if get_settings().app_env != "development":
        raise DevelopmentOnly()
    if repo.by_email(session, DEV_ADMIN_EMAIL) is not None:
        return None

    user = repo.create(session, email=DEV_ADMIN_EMAIL, role="gestor")
    user.senha_hash = hash_password(DEV_ADMIN_PASSWORD)
    user.status = "ativo"
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="usuario.gestor_inicial",
            user_id=None,
            dados_anteriores={"perfil": "gestor", "mecanismo": "semente_desenvolvimento"},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user


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
    row = credentials.redeem(session, value=token, kind=credentials.INVITE, at=at)
    credentials.require_strong_password(password)

    user = repo.by_id(session, row.user_id)
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
            user_id=user.id,
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


def block(
    session: Session,
    *,
    actor: User,
    user_id: uuid.UUID,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> User:
    """Block an account (AC-0001-12).

    The unexpired access token stops working immediately, because
    `app/core/authorization.py` checks `ativo` on every request; nothing here
    has to reach into the session store for that. Revoking the refresh rows is
    still right: it is what makes the trail show the session ended rather than
    leaving it dangling.
    """
    return _change_status(
        session,
        actor=actor,
        user_id=user_id,
        new_status="bloqueado",
        acao="usuario.bloqueado",
        at=at,
        correlation_id=correlation_id,
    )


def unblock(
    session: Session,
    *,
    actor: User,
    user_id: uuid.UUID,
    justification: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> User:
    """Restore a blocked account to `ativo` (AC-0001-44).

    The justification mirrors RN03: unblocking undoes a decision another gestor
    took, so it is recorded in the audit row's `justificativa` column, never
    silent. Nothing here can empty the gestor role, so unlike `block` it needs
    no last-gestor guard, and it restores no session: the ones the block revoked
    stay revoked and the member signs in again.
    """
    user = repo.by_id(session, user_id)
    if user is None:
        raise UsuarioNotFound()
    if user.status != "bloqueado":
        raise NotBlocked()

    user.status = "ativo"
    session.flush()
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="usuario.desbloqueado",
            user_id=actor.id,
            dados_anteriores={"status": "bloqueado"},
            justificativa=justification.strip(),
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user


def deactivate(
    session: Session,
    *,
    actor: User,
    user_id: uuid.UUID,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> User:
    """Deactivate and anonymise, preserving the history (AC-0001-14, RN16).

    LGPD art. 16, I: the person's identifying fields go, the record of what they
    did stays. `pseudonimo` is a generated column, so every audit row keeps
    resolving to the same stable name without the history being rewritten, which
    it could not be anyway since AC-0001-27 makes it immutable.
    """
    user = _change_status(
        session,
        actor=actor,
        user_id=user_id,
        new_status="desativado",
        acao="usuario.desativado",
        at=at,
        correlation_id=correlation_id,
    )
    # All five together, or the CHECK refuses the row. A half-anonymised usuario
    # is the state somebody later "restores" the name from the leftovers.
    user.nome = None
    user.email = None
    user.registro_funcional = None
    user.senha_hash = None
    user.oidc_subject = None
    user.anonimizado_em = at
    session.flush()
    return user


def list_members(session: Session, *, page: int, size: int) -> tuple[Sequence[User], int]:
    """One page of members, and the total."""
    return repo.list_page(session, page=page, size=size), repo.count(session)


def _change_status(
    session: Session,
    *,
    actor: User,
    user_id: uuid.UUID,
    new_status: str,
    acao: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> User:
    # Before reading the count, never after: see `repo.lock_gestores`.
    repo.lock_gestores(session)

    user = repo.by_id(session, user_id)
    if user is None:
        raise UsuarioNotFound()

    previous = user.status
    if previous == new_status:
        return user

    if (
        user.role == "gestor"
        and previous == "ativo"
        and repo.count_active_gestores(session, excluding=user.id) == 0
    ):
        _audit_last_gestor(session, actor=actor, target=user, correlation_id=correlation_id)
        raise LastGestor()

    user.status = new_status
    try:
        session.flush()
    except DBAPIError as exc:
        # The trigger is still there, and under concurrency it can win the race
        # to refuse. Mapping both of its shapes keeps AC-0001-29 answering 409
        # instead of 500 on the path the advisory lock did not cover.
        if _sqlstate(exc) in (SQLSTATE_DEADLOCK, SQLSTATE_LAST_GESTOR):
            raise LastGestor() from exc
        raise

    repo_session.revoke_for_usuario(session, user.id, reason=REVOCATION_REASON[new_status], at=at)
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao=acao,
            user_id=actor.id,
            dados_anteriores={"status": previous},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user


def _audit_last_gestor(
    session: Session, *, actor: User, target: User, correlation_id: uuid.UUID
) -> None:
    """Record the blocked attempt (SPEC-0001 §8).

    Written in the caller's transaction on purpose, unlike the failed-login
    path: this one raises a `DomainError` the API turns into a 409, and the
    request's session still commits. Nothing was mutated, so there is no
    mutation for the row to be torn away from.
    """
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=actor.id,
            acao="usuario.ultimo_gestor",
            user_id=actor.id,
            dados_anteriores={"alvo_id": str(target.id)},
        ),
        correlation_id=correlation_id,
    )


def _sqlstate(exc: DBAPIError) -> str | None:
    original = getattr(exc, "orig", None)
    if isinstance(original, pgerrors.Error):
        return original.sqlstate
    return getattr(getattr(original, "diag", None), "sqlstate", None)


def trigger_reset(
    session: Session,
    *,
    actor: User,
    user_id: uuid.UUID,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> tuple[User, str]:
    """Issue a reset grant for a member, at a gestor's request (AC-0001-32).

    Returns the usuario and the link. **The gestor receives the link**, which is
    a deliberate loss of a property the criterion originally had: with no mail
    transport there is no channel to the member, and a reset that reaches nobody
    is not a reset. SPEC-0001 v1.0 records what this costs. The act is audited
    with the gestor as actor and the member as target, and redeeming revokes
    every session, so the member sees it happen.
    """
    user = repo.by_id(session, user_id)
    if user is None:
        raise UsuarioNotFound()

    grant = credentials.issue(
        session,
        user_id=user.id,
        kind=credentials.RESET,
        at=at,
        created_by=actor.id,
    )
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="usuario.redefinicao_solicitada",
            user_id=actor.id,
            # Actor and target are different people here, which is the whole
            # reason this row has to exist.
            dados_anteriores={"alvo_id": str(user.id)},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user, grant.link("/reset-password")


def redeem_reset(
    session: Session,
    *,
    token: str,
    password: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> User:
    """Replace the credential and end every session (AC-0001-31).

    Revoking every session is the criterion rather than hygiene, and it cuts
    both ways on purpose. If the person reset because they suspect theft, it
    evicts the thief; if a thief holding the link did the reset, it evicts the
    owner, who then notices. Leaving old sessions alive would make the reset
    cosmetic in exactly the case that matters.
    """
    row = credentials.redeem(
        session,
        value=token,
        kind=credentials.RESET,
        at=at,
        already_used=ResetAlreadyUsed,
        expired=ResetExpired,
    )
    # Before spending the grant, so a password that fails the policy leaves the
    # link usable (AC-0001-31's last clause).
    credentials.require_strong_password(password)

    user = repo.by_id(session, row.user_id)
    if user is None:  # pragma: no cover - the foreign key makes this unreachable
        raise UsuarioNotFound()

    user.senha_hash = hash_password(password)
    credentials.consume(session, row, at=at)
    revoked = repo_session.revoke_for_usuario(session, user.id, reason="redefinicao", at=at)
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="usuario.redefinicao_concluida",
            user_id=user.id,
            dados_anteriores={"sessoes_revogadas": revoked},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return user
