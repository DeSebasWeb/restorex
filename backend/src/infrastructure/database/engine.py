"""Database engine and session management.

On startup, runs auto-migrations to ensure the schema is up to date.
Retries connection if the database is not ready yet.
"""

import logging
import time
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.database.models import Base

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None
_database_url = None


def get_engine():
    return _engine


def get_session() -> Session:
    global _engine, _SessionLocal
    if _SessionLocal is None:
        # Auto-retry init if not ready yet
        if _database_url:
            try:
                init_db(_database_url)
            except Exception:
                pass
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
    _database_url = database_url

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Initializing database (attempt %d/%d): %s", attempt, max_retries, _mask_url(database_url))

            _ensure_database_exists(database_url)

            _engine = create_engine(database_url, pool_pre_ping=True, pool_size=5, echo=False)
            _SessionLocal = sessionmaker(bind=_engine)

            # Auto-migrate
            Base.metadata.create_all(bind=_engine)
            logger.info("Schema synchronized (create_all).")

            _run_alembic_migrations()

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

    admin_url = parsed.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    try:
        with admin_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            )
            if not result.fetchone():
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info("Created database: %s", db_name)
            else:
                logger.info("Database already exists: %s", db_name)
    finally:
        admin_engine.dispose()


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
