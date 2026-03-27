"""Database engine and session management.

On startup, runs auto-migrations to ensure the schema is up to date.
Retries connection if the database is not ready yet.
"""

import logging
import re
import threading
import time
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.database.models import Base

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None
_database_url = None
_init_lock = threading.Lock()

# Strict: only alphanumeric and underscores, max 63 chars (PG identifier limit)
_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def _validate_identifier(name: str) -> str:
    """Validate a PostgreSQL identifier to prevent SQL injection."""
    if not _SAFE_IDENTIFIER.match(name):
        raise ValueError(f"Invalid PostgreSQL identifier: {name!r}")
    return name


def get_engine():
    return _engine


def get_session() -> Session:
    global _engine, _SessionLocal
    if _SessionLocal is None:
        if _database_url:
            try:
                init_db(_database_url)
            except Exception as e:
                logger.warning("Auto-retry init_db failed: %s", e)
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionLocal()


@contextmanager
def session_scope():
    """Context manager that commits on success and rolls back on error."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(database_url: str, max_retries: int = 5, retry_delay: float = 3.0) -> None:
    """Initialize the database engine with retry logic for startup ordering."""
    global _engine, _SessionLocal, _database_url

    with _init_lock:
        _database_url = database_url

        for attempt in range(1, max_retries + 1):
            try:
                logger.info("Initializing database (attempt %d/%d): %s", attempt, max_retries, _mask_url(database_url))

                _ensure_database_exists(database_url)

                _engine = create_engine(database_url, pool_pre_ping=True, pool_size=5, echo=False)
                _SessionLocal = sessionmaker(bind=_engine)

                # Auto-migrate: schema updates for existing tables
                _fix_db_stats_constraint()
                # Create any new tables
                Base.metadata.create_all(bind=_engine)
                # Add missing columns to existing tables
                _add_missing_columns()
                logger.info("Schema synchronized.")

                _run_alembic_migrations()

                # Seed auth data (roles, permissions, default admin)
                from src.infrastructure.database.seed import seed_auth_data
                seed_auth_data()

                logger.info("Database initialized successfully.")
                return

            except Exception as e:
                logger.warning("Database init attempt %d failed: %s", attempt, e)
                _engine = None
                _SessionLocal = None
                if attempt < max_retries:
                    logger.info("Retrying in %.0fs...", retry_delay)
                    time.sleep(retry_delay)
                else:
                    logger.error("Database initialization failed after %d attempts.", max_retries)
                    raise


def _ensure_database_exists(url: str) -> None:
    """Connect to the default 'postgres' database and create our database if it doesn't exist."""
    from sqlalchemy.engine.url import make_url
    parsed = make_url(url)
    db_name = parsed.database

    # Validate database name to prevent SQL injection
    _validate_identifier(db_name)

    admin_url = parsed.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    try:
        with admin_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            )
            if not result.fetchone():
                # Safe: db_name validated by _validate_identifier above
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info("Created database: %s", db_name)
            else:
                logger.info("Database already exists: %s", db_name)
    finally:
        admin_engine.dispose()


def _fix_db_stats_constraint() -> None:
    """Migrate db_stats from unique(db_name) to unique(db_name, source)."""
    try:
        with _engine.begin() as conn:
            # Check if 'source' column exists
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'db_stats' AND column_name = 'source'"
            ))
            if not result.fetchone():
                # Drop old unique constraint on db_name
                conn.execute(text('ALTER TABLE db_stats DROP CONSTRAINT IF EXISTS db_stats_db_name_key'))
                conn.execute(text('DROP INDEX IF EXISTS ix_db_stats_db_name'))
                # Add source column
                conn.execute(text("ALTER TABLE db_stats ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'scan'"))
                # Add new composite unique index
                conn.execute(text(
                    'CREATE UNIQUE INDEX IF NOT EXISTS ix_db_stats_db_name_source ON db_stats (db_name, source)'
                ))
                logger.info("Migrated db_stats: added source column with composite unique index.")
    except Exception as e:
        logger.warning("db_stats migration skipped: %s", e)


def _add_missing_columns() -> None:
    """Detect and add columns that exist in models but not in the database.

    This handles the case where create_all() skips columns on existing tables.
    All identifiers are validated to prevent SQL injection.
    """
    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(_engine)
    with _engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue

            # Validate table name
            _validate_identifier(table.name)

            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing:
                    # Validate column name
                    _validate_identifier(column.name)

                    col_type = column.type.compile(dialect=_engine.dialect)
                    nullable = "" if column.nullable else " NOT NULL"

                    # Handle defaults safely: skip callable defaults (like datetime.now),
                    # they are Python-side and don't need a SQL DEFAULT clause
                    default = ""
                    if column.server_default is not None:
                        # server_default is a SQL expression, safe to use
                        default = f" DEFAULT {column.server_default.arg.text}"
                    elif column.default is not None and not callable(column.default.arg):
                        # Literal value default — use parameterized
                        default = f" DEFAULT {column.default.arg!r}"

                    sql = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}{nullable}{default}'
                    conn.execute(text(sql))
                    logger.info("Added missing column: %s.%s (%s)", table.name, column.name, col_type)


def _run_alembic_migrations() -> None:
    """Run pending Alembic migrations if the migrations directory exists."""
    try:
        from alembic.config import Config
        from alembic import command
        from pathlib import Path

        migrations_dir = Path(__file__).parent / "migrations"
        alembic_ini = migrations_dir / "alembic.ini"

        if not alembic_ini.exists():
            return

        alembic_cfg = Config(str(alembic_ini))
        alembic_cfg.set_main_option("script_location", str(migrations_dir))
        alembic_cfg.set_main_option("sqlalchemy.url", str(_engine.url))

        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied.")

    except Exception as e:
        logger.warning("Alembic migration skipped: %s", e)


def _mask_url(url: str) -> str:
    """Mask password in database URL for logging."""
    try:
        from sqlalchemy.engine.url import make_url
        parsed = make_url(url)
        return str(parsed.set(password="****"))
    except Exception:
        return "***"
