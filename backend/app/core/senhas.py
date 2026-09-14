"""Password hashing (AC-0001-05).

bcrypt at the configured cost, which AC-0001-05 pins at 12 or higher. ADR-0011
records the consequence and accepts it: a cost-12 verification costs roughly
250–400 ms *by design*, so the two routes that run it sit outside RNF01's
latency budget. Lowering the cost to meet that budget would be a security
downgrade wearing the clothes of a performance fix.

The password is SHA-256'd before bcrypt sees it. bcrypt silently truncates its
input at 72 bytes, so without this a long passphrase would have its tail
ignored — and silently, which is the worst way for a credential to be weaker
than the user believes. Base64 rather than hex so the digest fits well inside
the limit.
"""

from __future__ import annotations

import base64
import hashlib

import bcrypt

from app.core.config import get_settings


def _preparar(senha: str) -> bytes:
    return base64.b64encode(hashlib.sha256(senha.encode()).digest())


def hash_senha(senha: str) -> str:
    custo = get_settings().bcrypt_cost
    return bcrypt.hashpw(_preparar(senha), bcrypt.gensalt(rounds=custo)).decode()


def check_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        return bcrypt.checkpw(_preparar(senha), hash_armazenado.encode())
    except ValueError:
        # A malformed stored hash must not authenticate anyone, and must not
        # crash the login route either — a 500 here would tell an attacker they
        # found an account in a broken state.
        return False
