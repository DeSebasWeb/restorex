"""Concrete adapter: PostgreSQL inspector via remote psql commands.

Implements the DatabaseInspector port by running psql through
an injected RemoteExecutor (SSH).

SECURITY: All database names are validated through DbName value object
before reaching any shell command or SQL query.
"""

import logging
import shlex

from src.domain.ports.database_inspector import DatabaseInspector
from src.domain.ports.remote_executor import RemoteExecutor
from src.domain.value_objects.db_change_stats import DbChangeStats
from src.domain.value_objects.db_name import DbName
from src.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class PostgresAdapter(DatabaseInspector):
    def __init__(self, executor: RemoteExecutor):
        self._exec = executor

    def _psql(self, sql: str, db_name: str = "postgres") -> str:
        """Run a psql command remotely via SSH.

        PGPASSWORD is passed as env var. All arguments are shell-quoted via shlex.
        SQL is passed via -c flag with proper escaping.
        """
        psql_cmd = (
            f"psql -h {shlex.quote(Settings.PG_HOST)} "
            f"-p {shlex.quote(str(Settings.PG_PORT))} "
            f"-U {shlex.quote(Settings.PG_USER)} "
            f"-d {shlex.quote(db_name)} "
            f"-t -A --no-align"
        )

        safe_sql = sql.replace("'", "'\\''")
        cmd = f"PGPASSWORD={shlex.quote(Settings.PG_PASSWORD)} {psql_cmd} -c '{safe_sql}'"

        stdout, stderr, code = self._exec.execute(cmd)
        if code != 0:
            logger.error("psql failed (db=%s): %s", db_name, stderr)
            raise RuntimeError(f"psql error: {stderr}")
        return stdout

    def list_databases(self) -> list[str]:
        sql = (
            "SELECT datname FROM pg_database "
            "WHERE datistemplate = false ORDER BY datname"
        )
        raw = self._psql(sql)
        all_dbs = [d.strip() for d in raw.split("\n") if d.strip()]

        safe_dbs = []
        for name in all_dbs:
            if name in Settings.EXCLUDED_DBS:
                continue
            try:
                validated = DbName(name)
                safe_dbs.append(validated.value)
            except Exception:
                logger.warning("Skipping database with unsafe name: %r", name)

        return safe_dbs

    def get_change_stats(self, db_name: str) -> DbChangeStats:
        validated = DbName(db_name)

        # Use pg_stat_user_tables for change counters (I/U/D)
        # and pg_class for reliable row estimates (doesn't depend on ANALYZE being recent)
        sql = (
            "SELECT "
            "COALESCE(SUM(s.n_tup_ins),0), "
            "COALESCE(SUM(s.n_tup_upd),0), "
            "COALESCE(SUM(s.n_tup_del),0), "
            "COALESCE(SUM(c.reltuples::bigint),0), "
            "COUNT(*) "
            "FROM pg_stat_user_tables s "
            "JOIN pg_class c ON c.relname = s.relname AND c.relkind = 'r'"
        )
        try:
            raw = self._psql(sql, validated.value)
            parts = raw.split("|")
            if len(parts) >= 5:
                return DbChangeStats(
                    inserts=int(parts[0]),
                    updates=int(parts[1]),
                    deletes=int(parts[2]),
                    live_rows=max(int(parts[3]), 0),
                    table_count=int(parts[4]),
                )
        except Exception:
            logger.warning("Could not get stats for %s", db_name, exc_info=True)

        return DbChangeStats(0, 0, 0, 0, 0)

    def get_size_pretty(self, db_name: str) -> str:
        validated = DbName(db_name)

        # Query from the target database itself to ensure access
        sql = f"SELECT pg_size_pretty(pg_database_size(current_database()))"
        try:
            return self._psql(sql, validated.value).strip()
        except Exception:
            return "Unknown"
