"""SQLAlchemy models for the pg_backup_manager database."""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Text, Boolean,
    DateTime, ForeignKey, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class BackupRunModel(Base):
    """A single execution of the backup workflow."""
    __tablename__ = "backup_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, nullable=False, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)
    total_dbs = Column(Integer, nullable=False, default=0)
    backed_up = Column(Integer, nullable=False, default=0)
    skipped = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)

    results = relationship("BackupResultModel", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_backup_runs_started_at", "started_at"),
    )


class BackupResultModel(Base):
    """Result of backing up a single database within a run."""
    __tablename__ = "backup_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("backup_runs.id", ondelete="CASCADE"), nullable=False)
    db_name = Column(String(128), nullable=False)
    status = Column(String(20), nullable=False)  # success, failed, skipped
    timestamp = Column(String(64), nullable=True)
    backup_file = Column(Text, nullable=True)
    sql_file = Column(Text, nullable=True)
    backup_size = Column(BigInteger, nullable=False, default=0)
    sql_size = Column(BigInteger, nullable=False, default=0)
    duration_seconds = Column(Float, nullable=False, default=0.0)
    error = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)

    run = relationship("BackupRunModel", back_populates="results")

    __table_args__ = (
        Index("ix_backup_results_db_name", "db_name"),
        Index("ix_backup_results_run_id", "run_id"),
    )


class DbStatsModel(Base):
    """Change statistics for a database (used for smart change detection)."""
    __tablename__ = "db_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    db_name = Column(String(128), nullable=False, unique=True)
    inserts = Column(BigInteger, nullable=False, default=0)
    updates = Column(BigInteger, nullable=False, default=0)
    deletes = Column(BigInteger, nullable=False, default=0)
    live_rows = Column(BigInteger, nullable=False, default=0)
    table_count = Column(Integer, nullable=False, default=0)
    size_pretty = Column(String(32), nullable=True)
    saved_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("ix_db_stats_db_name", "db_name"),
    )


class AppSettingModel(Base):
    """Key-value store for application settings (replaces settings.json)."""
    __tablename__ = "app_settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class BackupProgressModel(Base):
    """Live progress tracking for running backups. One row, updated in-place."""
    __tablename__ = "backup_progress"

    id = Column(Integer, primary_key=True, default=1)
    running = Column(Boolean, nullable=False, default=False)
    started_at = Column(DateTime, nullable=True)
    current_db = Column(String(128), nullable=True)
    current_step = Column(String(255), nullable=True)  # e.g. "Generating .backup"
    processed = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)
    last_completed_db = Column(String(128), nullable=True)
    last_completed_status = Column(String(20), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
