"""Model: Key-value store for application settings."""

from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime

from .base import Base


class AppSettingModel(Base):
    __tablename__ = "app_settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
