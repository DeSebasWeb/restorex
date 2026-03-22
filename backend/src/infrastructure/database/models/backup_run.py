"""Model: A single execution of the backup workflow."""

from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, Index
from sqlalchemy.orm import relationship

from .base import Base


class BackupRunModel(Base):
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
