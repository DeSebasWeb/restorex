"""Model: Per-user notification channel configuration."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base


class UserNotificationChannelModel(Base):
    __tablename__ = "user_notification_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(32), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    on_success = Column(Boolean, nullable=False, default=True)
    on_failure = Column(Boolean, nullable=False, default=True)
    on_partial = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    settings = relationship(
        "UserNotificationSettingModel",
        back_populates="channel_rel",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_user_notif_user_channel", "user_id", "channel", unique=True),
    )
