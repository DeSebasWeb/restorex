"""Model: Key-value store for per-user notification channel settings."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base


class UserNotificationSettingModel(Base):
    __tablename__ = "user_notification_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_channel_id = Column(
        Integer,
        ForeignKey("user_notification_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    key = Column(String(128), nullable=False)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    channel_rel = relationship("UserNotificationChannelModel", back_populates="settings")

    __table_args__ = (
        Index("ix_user_notif_setting_channel_key", "user_channel_id", "key", unique=True),
    )
