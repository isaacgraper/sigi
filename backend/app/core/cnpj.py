"""CNPJ normalisation and check-digit validation (data-model.md, FORNECEDOR)."""

from __future__ import annotations

import re

_WEIGHTS_FIRST = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_WEIGHTS_SECOND = (6, *_WEIGHTS_FIRST)


def digits_of(value: str) -> str:
    """Strip everything but the digits, so punctuation is presentation only."""
    return re.sub(r"\D", "", value)


def is_valid(value: str) -> bool:
    """Whether the value is a CNPJ: 14 digits, not all equal, check digits right."""
    cnpj = digits_of(value)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False
    first = _check_digit(cnpj[:12], _WEIGHTS_FIRST)
    second = _check_digit(cnpj[:12] + str(first), _WEIGHTS_SECOND)
    return cnpj[12:] == f"{first}{second}"


def _check_digit(base: str, weights: tuple[int, ...]) -> int:
    total = sum(int(d) * w for d, w in zip(base, weights, strict=True))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder
