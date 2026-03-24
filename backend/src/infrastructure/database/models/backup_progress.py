"""Model: Live progress tracking for running backups."""

from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Text

from .base import Base


class BackupProgressModel(Base):
    __tablename__ = "backup_progress"

    id = Column(Integer, primary_key=True, default=1)
    running = Column(Boolean, nullable=False, default=False)
    started_at = Column(DateTime, nullable=True)
    current_db = Column(String(128), nullable=True)
    current_step = Column(String(255), nullable=True)
    processed = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)
    last_completed_db = Column(String(128), nullable=True)
    last_completed_status = Column(String(20), nullable=True)
    download_bytes = Column(BigInteger, nullable=False, default=0)
    download_total = Column(BigInteger, nullable=False, default=0)
    active_jobs = Column(Text, nullable=False, default="[]")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
