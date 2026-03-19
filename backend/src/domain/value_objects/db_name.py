"""Value object: Validated database name.

Ensures database names are safe before they reach any shell command or SQL query.
PostgreSQL identifiers: letters, digits, underscores. Max 63 chars.
"""

import re

from src.domain.exceptions import DomainError


_SAFE_DB_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


class InvalidDatabaseName(DomainError):
    """Database name contains unsafe characters."""


class DbName:
    """Immutable, validated database name. Safe for shell and SQL use."""

    __slots__ = ("_value",)

    def __init__(self, raw: str):
        raw = raw.strip()
        if not _SAFE_DB_NAME.match(raw):
            raise InvalidDatabaseName(
                f"Unsafe database name rejected: {raw!r}. "
                "Only letters, digits, and underscores allowed (max 63 chars)."
            )
        self._value = raw

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"DbName({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DbName):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)
