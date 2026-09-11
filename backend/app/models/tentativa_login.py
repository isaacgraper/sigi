"""`TENTATIVA_LOGIN` — the per-address lockout of AC-0001-03.

Keyed on an HMAC of the *submitted* address rather than on a usuario. Keying it
on the account made AC-0001-02 false: an unknown address had no counter, so six
attempts told an attacker which addresses exist.
"""

from __future__ import annotations

import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TentativaLogin(Base):
    __tablename__ = "tentativa_login"

    email_hmac: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    tentativas: Mapped[int] = mapped_column(Integer, server_default="0")
    # What makes the fifteen-minute window expressible. A counter alone states
    # only "five failures ever", which would lock an account over failures
    # spread across days.
    ultima_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    bloqueado_ate: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (CheckConstraint("tentativas >= 0", name="ck_tentativa_nao_negativa"),)
