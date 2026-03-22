"""Model: Result of backing up a single database within a run."""

from sqlalchemy import Column, Integer, BigInteger, String, Float, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base


class BackupResultModel(Base):
    __tablename__ = "backup_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("backup_runs.id", ondelete="CASCADE"), nullable=False)
    db_name = Column(String(128), nullable=False)
    status = Column(String(20), nullable=False)
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
