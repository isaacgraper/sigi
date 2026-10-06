"""`FORNECEDOR` — who sells under an ATA (data-model.md)."""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Fornecedor(Base):
    """A supplier. Found by its CNPJ, created by the first ATA that names it (AC-0002-25).

    The CNPJ is stored as its 14 digits, so two spellings of one company are one
    row; punctuation is presentation.
    """

    __tablename__ = "fornecedor"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    cnpj: Mapped[str] = mapped_column(String(14), unique=True)
    legal_name: Mapped[str] = mapped_column("razao_social", String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    ativo: Mapped[bool] = mapped_column(Boolean, server_default="true")
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
