"""Model: A notification channel with toggle and trigger preferences."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship

from .base import Base


class NotificationChannelModel(Base):
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel = Column(String(32), nullable=False, unique=True)
    enabled = Column(Boolean, nullable=False, default=False)
    on_success = Column(Boolean, nullable=False, default=True)
    on_failure = Column(Boolean, nullable=False, default=True)
    on_partial = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    settings = relationship("NotificationSettingModel", back_populates="channel_rel", cascade="all, delete-orphan")
