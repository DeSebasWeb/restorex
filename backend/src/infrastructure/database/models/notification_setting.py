"""Model: Key-value store for channel-specific notification configuration."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base


class NotificationSettingModel(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(128), nullable=False)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    channel_rel = relationship("NotificationChannelModel", back_populates="settings")

    __table_args__ = (
        Index("ix_notification_settings_channel_key", "channel_id", "key", unique=True),
    )
