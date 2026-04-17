"""Helpers for SQLAlchemy enums backed by enum values."""

from sqlalchemy import Enum as SQLEnum


def value_enum(enum_cls, **kwargs):
    """Persist and load enum.value instead of enum member names."""
    return SQLEnum(
        enum_cls,
        values_callable=lambda enum: [item.value for item in enum],
        validate_strings=True,
        **kwargs,
    )
