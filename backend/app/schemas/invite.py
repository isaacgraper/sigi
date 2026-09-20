"""Request and response bodies for redeeming an invitation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.auth import SessionOutput


class ActivationInput(BaseModel):
    """The body of an activation.

    The token is a field rather than a path segment (OQ-31). A single-use
    credential in a URL path lands in access logs, proxy logs and browser
    history, none of which this project controls.
    """

    token: str = Field(min_length=1)
    # No `min_length` on the password on purpose. The policy lives in
    # `credentials.require_strong_password`, which raises WEAK_PASSWORD with the
    # rule in the message. AC-0001-26 asks for that code, not a generic 422, and
    # two places stating the minimum is how they come to disagree.
    password: str = Field(min_length=1)


class ActivationOutput(BaseModel):
    """Activation and first login are one step (AC-0001-11)."""

    sessao: SessionOutput
