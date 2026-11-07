"""The base of every request body that stores text.

A control character is never typed by a servidor: it arrives pasted from
another system or sent on purpose. PostgreSQL refuses a NUL in a text column,
which surfaced as a 500, and the others would be stored and shown back as
invisible bytes. Each is refused on its own field, so the screen shows it under
that input (AC-0001-41).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError

from app.constants.text import CONTROL_CHARACTER, CONTROL_CHARACTER_MESSAGE


class RequestBody(BaseModel):
    """A body whose text fields refuse control characters."""

    @field_validator("*", mode="before")
    @classmethod
    def _no_control_character(cls, value: Any) -> Any:
        if isinstance(value, str) and CONTROL_CHARACTER.search(value):
            raise PydanticCustomError(
                "control_character", "{message}", {"message": CONTROL_CHARACTER_MESSAGE}
            )
        return value
