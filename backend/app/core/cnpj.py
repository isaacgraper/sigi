"""CNPJ normalisation and check-digit validation (SPEC-0002 AC-0002-25).

Since July 2026 the Receita Federal also issues alphanumeric CNPJs (IN RFB nº
2.229/2024): twelve digits or uppercase letters, then two numeric check digits,
computed as before with each character valued at its ASCII code minus 48. A
numeric CNPJ is the case with no letters, so one rule covers both.
"""

from __future__ import annotations

import re

_WEIGHTS_FIRST = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_WEIGHTS_SECOND = (6, *_WEIGHTS_FIRST)
_SHAPE = re.compile(r"^[0-9A-Z]{12}[0-9]{2}$")


def normalise(value: str) -> str:
    """Drop the punctuation people type and uppercase the letters.

    Only `.`, `/`, `-` and spaces go: anything else stays and fails the shape,
    so a typo is refused rather than silently removed.
    """
    return re.sub(r"[./\-\s]", "", value).upper()


def is_valid(value: str) -> bool:
    """Whether the value is a CNPJ: right shape, not one repeated character, check digits right."""
    cnpj = normalise(value)
    if not _SHAPE.fullmatch(cnpj) or len(set(cnpj)) == 1:
        return False
    first = _check_digit(cnpj[:12], _WEIGHTS_FIRST)
    second = _check_digit(cnpj[:12] + str(first), _WEIGHTS_SECOND)
    return cnpj[12:] == f"{first}{second}"


def _check_digit(base: str, weights: tuple[int, ...]) -> int:
    total = sum((ord(c) - 48) * w for c, w in zip(base, weights, strict=True))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder
