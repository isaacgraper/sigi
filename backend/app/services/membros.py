"""Member management (SPEC-0001 §4.2 — AC-0001-10 to -14, -25, -26, -28, -29).

This is the module that creates accounts. There is no self-registration and no
just-in-time provisioning from the identity provider (AC-0001-21), so every
usuario in the system passes through `convidar` — which also means a defect here
is a defect in who can enter the system at all.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Sequence

from psycopg import errors as pgerros
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.senhas import gerar_hash
from app.models.usuario import Usuario
from app.repositories import sessao as repo_sessao
from app.repositories import usuario as repo
from app.services import credenciais
from app.services.auditoria import Evento, registrar
from app.services.erros import (
    DominioNaoInstitucional,
    EmailJaCadastrado,
    UltimoGestor,
    UsuarioNaoEncontrado,
)

# PostgreSQL raises this when the last-gestor trigger's `FOR UPDATE` deadlocks
# against a concurrent removal. Measured over 40 runs of the AC-0001-29 race:
# exactly one deactivation always succeeds, and the loser sees a deadlock 39
# times and the trigger's own SI005 once. Both mean the same thing to the
# caller, so both become 409.
SQLSTATE_DEADLOCK = "40P01"
SQLSTATE_ULTIMO_GESTOR = "SI005"

# `ck_sessao_motivo_valor` fixa o vocabulário de `sessao.revogado_motivo`, e
# ele não é o mesmo de `usuario.status`. São duas linguagens: uma descreve a
# conta, a outra por que a sessão terminou.
MOTIVO_DA_REVOGACAO = {"bloqueado": "bloqueio", "desativado": "desativacao"}


def convidar(
    sessao: Session,
    *,
    ator: Usuario,
    email: str,
    perfil: str,
    agora: datetime.datetime,
    correlation_id: uuid.UUID,
) -> tuple[Usuario, str]:
    """Create a `pendente` account and issue its activation link (AC-0001-10).

    Returns the usuario and the link. The link exists in memory for the length
    of this response and nowhere else — only its HMAC is stored — so the caller
    must hand it to the gestor and must not log it.
    """
    cfg = get_settings()
    endereco = email.strip().lower()
    _exigir_dominio_institucional(endereco, cfg.dominios_institucionais)

    if repo.por_email(sessao, endereco) is not None:
        # In any status, including `desativado`. A second account for one person
        # splits their audit trail in two, and neither half answers "what did
        # this person do" (AC-0001-28).
        raise EmailJaCadastrado()

    usuario = repo.criar(sessao, email=endereco, perfil=perfil)
    grant = credenciais.emitir(
        sessao,
        usuario_id=usuario.id,
        tipo=credenciais.CONVITE,
        agora=agora,
        criado_por=ator.id,
    )
    registrar(
        sessao,
        Evento(
            entidade_tipo="usuario",
            entidade_id=usuario.id,
            acao="usuario.convidado",
            usuario_id=ator.id,
            # The perfil granted, never the token: this table can never be
            # corrected, and `lgpd.md` promises it carries no credential.
            dados_anteriores={"perfil": perfil},
        ),
        correlation_id=correlation_id,
        momento=agora,
    )
    return usuario, grant.link("/convite")


def ativar(
    sessao: Session,
    *,
    token: str,
    senha: str,
    agora: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Usuario:
    """Redeem an invitation and set the credential (AC-0001-11, -25, -26).

    Order matters and is the criterion: the password is validated **before** the
    grant is spent, so a password that fails the policy leaves the invitation
    usable. A typo must not burn it and force the gestor to issue another.
    """
    linha = credenciais.resgatar(sessao, valor=token, tipo=credenciais.CONVITE, agora=agora)
    credenciais.exigir_senha_forte(senha)

    usuario = repo.por_id(sessao, linha.usuario_id)
    if usuario is None:  # pragma: no cover - FK makes this unreachable
        raise UsuarioNaoEncontrado()

    usuario.senha_hash = gerar_hash(senha)
    usuario.status = "ativo"
    credenciais.consumir(sessao, linha, agora=agora)
    registrar(
        sessao,
        Evento(
            entidade_tipo="usuario",
            entidade_id=usuario.id,
            acao="usuario.ativado",
            usuario_id=usuario.id,
            dados_anteriores={"status": "pendente"},
        ),
        correlation_id=correlation_id,
        momento=agora,
    )
    return usuario


def bloquear(
    sessao: Session,
    *,
    ator: Usuario,
    usuario_id: uuid.UUID,
    agora: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Usuario:
    """Block an account (AC-0001-12).

    The unexpired access token stops working immediately because
    `app/core/autorizacao.py` checks `ativo` on every request — nothing here has
    to reach into the session store for that. Revoking the refresh rows is still
    right: it is what makes the trail show the session ended rather than leaving
    it dangling.
    """
    return _mudar_status(
        sessao,
        ator=ator,
        usuario_id=usuario_id,
        novo_status="bloqueado",
        acao="usuario.bloqueado",
        agora=agora,
        correlation_id=correlation_id,
    )


def desativar(
    sessao: Session,
    *,
    ator: Usuario,
    usuario_id: uuid.UUID,
    agora: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Usuario:
    """Deactivate and anonymise, preserving the history (AC-0001-14, RN16).

    LGPD art. 16, I: the person's identifying fields go, the record of what they
    did stays. `pseudonimo` is a generated column, so every audit row keeps
    resolving to the same stable name without the history being rewritten —
    which it could not be, since AC-0001-27 makes it immutable.
    """
    usuario = _mudar_status(
        sessao,
        ator=ator,
        usuario_id=usuario_id,
        novo_status="desativado",
        acao="usuario.desativado",
        agora=agora,
        correlation_id=correlation_id,
    )
    # All four together, or the CHECK refuses the row: a half-anonymised usuario
    # is the state where somebody later "restores" the name from the leftovers.
    usuario.nome = None
    usuario.email = None
    usuario.senha_hash = None
    usuario.oidc_subject = None
    usuario.anonimizado_em = agora
    sessao.flush()
    return usuario


def listar(sessao: Session, *, pagina: int, tamanho: int) -> tuple[Sequence[Usuario], int]:
    return repo.listar(sessao, pagina=pagina, tamanho=tamanho), repo.contar(sessao)


def _mudar_status(
    sessao: Session,
    *,
    ator: Usuario,
    usuario_id: uuid.UUID,
    novo_status: str,
    acao: str,
    agora: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Usuario:
    # Before reading the count, not after: see `repo.travar_gestores`.
    repo.travar_gestores(sessao)

    usuario = repo.por_id(sessao, usuario_id)
    if usuario is None:
        raise UsuarioNaoEncontrado()

    anterior = usuario.status
    if anterior == novo_status:
        return usuario

    if (
        usuario.perfil == "gestor"
        and anterior == "ativo"
        and repo.contar_gestores_ativos(sessao, exceto=usuario.id) == 0
    ):
        _auditar_ultimo_gestor(sessao, ator=ator, alvo=usuario, correlation_id=correlation_id)
        raise UltimoGestor()

    usuario.status = novo_status
    try:
        sessao.flush()
    except DBAPIError as exc:
        # The trigger is still there, and under concurrency it can win the race
        # to refuse. Mapping both of its shapes keeps AC-0001-29 answering 409
        # instead of 500 on the path the advisory lock did not cover.
        if _sqlstate(exc) in (SQLSTATE_DEADLOCK, SQLSTATE_ULTIMO_GESTOR):
            raise UltimoGestor() from exc
        raise

    repo_sessao.revogar_do_usuario(
        sessao, usuario.id, motivo=MOTIVO_DA_REVOGACAO[novo_status], momento=agora
    )
    registrar(
        sessao,
        Evento(
            entidade_tipo="usuario",
            entidade_id=usuario.id,
            acao=acao,
            usuario_id=ator.id,
            dados_anteriores={"status": anterior},
        ),
        correlation_id=correlation_id,
        momento=agora,
    )
    return usuario


def _auditar_ultimo_gestor(
    sessao: Session, *, ator: Usuario, alvo: Usuario, correlation_id: uuid.UUID
) -> None:
    """Record the blocked attempt (SPEC-0001 §8).

    Written in the caller's transaction on purpose, unlike the failed-login
    path: this one raises an `ErroDominio` that the API turns into a 409, and
    the request's session still commits. Nothing was mutated, so there is no
    mutation for the row to be torn away from.
    """
    registrar(
        sessao,
        Evento(
            entidade_tipo="usuario",
            entidade_id=ator.id,
            acao="usuario.ultimo_gestor",
            usuario_id=ator.id,
            dados_anteriores={"alvo_id": str(alvo.id)},
        ),
        correlation_id=correlation_id,
    )


def _sqlstate(exc: DBAPIError) -> str | None:
    original = getattr(exc, "orig", None)
    if isinstance(original, pgerros.Error):
        return original.sqlstate
    return getattr(getattr(original, "diag", None), "sqlstate", None)


def _exigir_dominio_institucional(email: str, permitidos: list[str]) -> None:
    _, _, dominio = email.rpartition("@")
    aceito = bool(dominio) and any(
        dominio == d.lower() or dominio.endswith(f".{d.lower()}") for d in permitidos
    )
    if not aceito:
        raise DominioNaoInstitucional(permitidos)
