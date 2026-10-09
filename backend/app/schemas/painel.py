"""Response body of the dashboard (SPEC-0012 §7)."""

from __future__ import annotations

from pydantic import BaseModel


class BlockOut(BaseModel):
    """One block's rows, each a list of its values as text in column order."""

    rows: list[list[str]]


class PainelOut(BaseModel):
    """Every block of one section, keyed by the block's id (AC-0012-12)."""

    section: str
    # True only for the development demonstration (AC-0012-13), so the page
    # can say so and nobody reads invented figures as the operation's.
    demo: bool
    blocks: dict[str, BlockOut]
