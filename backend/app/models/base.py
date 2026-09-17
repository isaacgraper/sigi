"""The declarative base every model inherits."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Carries the metadata Alembic compares the live schema against."""
