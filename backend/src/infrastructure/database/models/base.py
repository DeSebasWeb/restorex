"""SQLAlchemy declarative base. All models inherit from this."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
