"""Port: Database inspection interface.

Abstracts how we query PostgreSQL metadata. The domain doesn't
care if it's via SSH+psql, direct psycopg2, or any other method.
"""

from abc import ABC, abstractmethod

from src.domain.value_objects.db_change_stats import DbChangeStats


class DatabaseInspector(ABC):
    @abstractmethod
    def list_databases(self) -> list[str]:
        """Return names of all non-system databases."""

    @abstractmethod
    def get_change_stats(self, db_name: str) -> DbChangeStats:
        """Get INSERT/UPDATE/DELETE counters for a database."""

    @abstractmethod
    def get_size_pretty(self, db_name: str) -> str:
        """Get human-readable database size."""
