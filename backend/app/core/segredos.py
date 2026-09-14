"""Keyed hashing for values that must be correlatable but never readable.

Three places need the same primitive: the lockout counter keyed on a submitted
e-mail (AC-0001-03), the throttle keyed on a source address (AC-0001-33), and
the audit rows that record a refused authentication without storing the address
(SPEC-0001 §8). One implementation, because rotating the pepper is already a
one-way decision and having two would make it worse.

HMAC-SHA256 with a server-side pepper rather than a bare digest: the inputs are
low-entropy — an e-mail address, an IPv4 address — so a plain hash is reversible
by enumeration in seconds. The pepper lives in configuration and never in the
database, so a leaked dump alone does not let an attacker confirm a guess.

Not bcrypt or argon2 here. Those are for secrets a user chose; these values are
looked up by equality on an indexed column, and a salted hash cannot be looked
up at all.
"""

from __future__ import annotations

import hashlib
import hmac

from app.core.config import get_settings


def digest_secret(valor: str) -> bytes:
    """A stable, non-reversible 32-byte key for `valor`.

    Normalised to lowercase and stripped, so that `Ana@SC.gov.br ` and
    `ana@sc.gov.br` share a lockout counter — otherwise changing the case of one
    letter would reset an attacker's budget.
    """
    pepper = get_settings().hmac_pepper.encode()
    return hmac.new(pepper, valor.strip().lower().encode(), hashlib.sha256).digest()
