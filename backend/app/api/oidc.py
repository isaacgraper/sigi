"""Institutional OIDC routes (SPEC-0001 §7 — AC-0001-19 to -22)."""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.auth import _set_cookie
from app.core.config import get_settings
from app.core.correlation import current as current_correlation_id
from app.core.db import get_session
from app.core.throttling import enforce
from app.repositories import user as repo_user
from app.schemas.auth import SessionOutput
from app.services import oidc, sessions
from app.services.audit import Event, record, record_standalone
from app.services.errors import RouteUnavailable, UnprovisionedUsuario

router = APIRouter(prefix="/api/v1/auth/oidc", tags=["auth"], dependencies=[Depends(enforce)])

DbSession = Annotated[Session, Depends(get_session)]

STATE_COOKIE = "sigi_oidc_estado"


def _correlation_id(request: Request) -> uuid.UUID:
    raw = request.scope.get("state", {}).get("correlation_id")
    return raw if isinstance(raw, uuid.UUID) else current_correlation_id()


def _require_oidc() -> None:
    if not get_settings().oidc_enabled:
        raise RouteUnavailable()


@router.get("/authorize")
def authorize(response: Response) -> RedirectResponse:
    """Start institutional login (SPEC-0001 AC-0001-19)."""
    _require_oidc()
    cfg = get_settings()
    request_to_provider = oidc.start(now=datetime.datetime.now(datetime.UTC))

    redirect = RedirectResponse(request_to_provider.url, status_code=302)
    # The state travels in an httpOnly cookie, which is what binds it to this
    # caller: a state lifted from a URL is useless without it.
    redirect.set_cookie(
        STATE_COOKIE,
        request_to_provider.signed_state,
        max_age=cfg.oidc_state_ttl_minutes * 60,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="lax",
        path="/api/v1/auth/oidc",
    )
    return redirect


@router.get("/callback", response_model=SessionOutput)
def callback(
    code: str, state: str, request: Request, response: Response, session: DbSession
) -> SessionOutput:
    """Complete institutional login (SPEC-0001 AC-0001-19, -20, -21, -22)."""
    _require_oidc()
    now = datetime.datetime.now(datetime.UTC)
    correlation_id = _correlation_id(request)

    try:
        assertion = oidc.finish(
            code=code,
            received_state=state,
            signed_state=request.cookies.get(STATE_COOKIE),
            now=now,
        )
    except Exception as exc:
        _audit_refusal(reason=type(exc).__name__, email=None, correlation_id=correlation_id)
        raise

    user = repo_user.by_oidc_subject(session, assertion.subject)
    if user is None and assertion.email:
        user = repo_user.by_email(session, assertion.email)

    if user is None or not user.ativo:
        # No just-in-time provisioning: an account exists because a gestor
        # invited it, and for no other reason (AC-0001-21, I3).
        _audit_refusal(
            reason="sem_conta" if user is None else f"status_{user.status}",
            email=assertion.email,
            correlation_id=correlation_id,
        )
        raise UnprovisionedUsuario()

    # The first successful OIDC login binds the provider's stable subject, so
    # later logins no longer depend on the e-mail matching.
    if user.oidc_subject is None:
        user.oidc_subject = assertion.subject

    pair = sessions.open_session(
        session,
        user_id=user.id,
        # From the usuario record. The asserted group claim is recorded below
        # and consulted by nothing (AC-0001-22, I2).
        role=user.role,
        correlation_id=correlation_id,
        mechanism="oidc",
    )
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=user.id,
            acao="auth.oidc_claim",
            user_id=user.id,
            dados_anteriores={
                "claim_asserido": assertion.asserted_group,
                "perfil_aplicado": user.role,
            },
        ),
        correlation_id=correlation_id,
        at=now,
    )

    _set_cookie(response, pair.refresh_token)
    response.delete_cookie(STATE_COOKIE, path="/api/v1/auth/oidc")
    return SessionOutput(access_token=pair.access_token, expires_at=pair.expires_at)


def _audit_refusal(*, reason: str, email: str | None, correlation_id: uuid.UUID) -> None:
    """Record the refusal in its own committed transaction.

    The request is about to raise and its session will roll back, so a row
    written there would vanish with the refusal it records.
    """
    _, _, domain = (email or "").rpartition("@")
    record_standalone(
        Event(
            entidade_tipo="usuario",
            entidade_id=oidc.null_uuid(),
            acao="auth.oidc_recusada",
            user_id=None,
            dados_anteriores={
                "motivo": reason,
                "email_hmac": oidc.digest_for_audit(email),
                "dominio": domain or None,
            },
        ),
        correlation_id=correlation_id,
    )
