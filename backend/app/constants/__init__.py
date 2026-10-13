"""Fixed values the whole application shares (docs/process/coding-standards.md §7).

A value one domain owns lives in `app/constants/<domain>.py`. A value an
operator may tune without a deploy is configuration, in `app/core/config.py`.
These modules import nothing from `app`, so any layer may read them.
"""

from __future__ import annotations

from typing import Final
from zoneinfo import ZoneInfo

# ── Time ────────────────────────────────────────────────────────────────────

# Timestamps are stored UTC and presented in America/Sao_Paulo (CLAUDE.md), and a
# vigência ends on a calendar day of the entity, not of Greenwich.
LOCAL_TIMEZONE: Final = ZoneInfo("America/Sao_Paulo")

# ── HTTP ────────────────────────────────────────────────────────────────────

CORRELATION_HEADER: Final = "X-Correlation-Id"

MAX_BODY_BYTES: Final = 64 * 1024

# The API serves JSON only: a policy that allows nothing costs nothing, and a
# response can never be rendered or framed as a page.
SECURITY_HEADERS: Final = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
)

# The methods that change state, and so need an access decision (AC-0001-23).
WRITE_METHODS: Final = frozenset({"POST", "PUT", "PATCH", "DELETE"})
