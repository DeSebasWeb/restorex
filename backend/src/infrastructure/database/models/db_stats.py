"""Model: Change statistics for a database (scan display + backup detection)."""

from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Index

from .base import Base


class DbStatsModel(Base):
    """source='scan' for dashboard display, source='backup' for change detection."""
    __tablename__ = "db_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    db_name = Column(String(128), nullable=False)
    source = Column(String(16), nullable=False, default="scan")
    inserts = Column(BigInteger, nullable=False, default=0)
    updates = Column(BigInteger, nullable=False, default=0)
    deletes = Column(BigInteger, nullable=False, default=0)
    live_rows = Column(BigInteger, nullable=False, default=0)
    table_count = Column(Integer, nullable=False, default=0)
    size_pretty = Column(String(32), nullable=True)
    saved_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("ix_db_stats_db_name_source", "db_name", "source", unique=True),
    )
