"""Fixed values of the members of the entity (SPEC-0001)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

# Mirrors `ck_usuario_perfil`.
PERFIS: Final = ("gestor", "servidor", "auditor")

# Mirrors `ck_usuario_status`.
USUARIO_STATUS: Final = ("pendente", "ativo", "bloqueado", "desativado")

# The session's revocation reason when an account stops being active: the
# account's status in, the reason `ck_sessao_motivo_valor` accepts out.
STATUS_REVOCATION_REASON: Final = MappingProxyType(
    {"bloqueado": "bloqueio", "desativado": "desativacao"}
)

# PostgreSQL raises this when the last-gestor trigger's `FOR UPDATE` deadlocks
# against a concurrent removal. Measured over 40 runs of the AC-0001-29 race:
# exactly one deactivation always succeeds, and the loser sees a deadlock 39
# times and the trigger's own SI005 once. Both mean the same thing to the
# caller, so both become 409.
SQLSTATE_DEADLOCK: Final = "40P01"
SQLSTATE_LAST_GESTOR: Final = "SI005"

# Arbitrary but fixed: an advisory lock key is just a number both sides agree
# on. Named so that a second guard never picks the same one by accident.
LAST_GESTOR_LOCK_KEY: Final = 0x5163_0001

# The development-only seed (`app.cli seed-dev-admin`), refused outside development.
DEV_ADMIN_EMAIL: Final = "admin@sc.gov.br"
DEV_ADMIN_PASSWORD: Final = "admin"  # noqa: S105 - a development credential, refused elsewhere
