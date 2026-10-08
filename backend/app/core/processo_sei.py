"""The format of a Processo SEI number (SPEC-0004 AC-0004-03, SPEC-0002 AC-0002-08).

Format only. SIGI makes no request to SEI or to e-Publica (ADR-0002).
"""

from __future__ import annotations

import re

FORMAT = "NNNNN.NNNNNN/AAAA-DD"
_PATTERN = re.compile(r"^\d{5}\.\d{6}/\d{4}-\d{2}$")


def is_valid(value: str) -> bool:
    """Whether the value matches `NNNNN.NNNNNN/AAAA-DD`."""
    return _PATTERN.fullmatch(value.strip()) is not None
