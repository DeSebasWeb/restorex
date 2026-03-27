"""Permission model — granular resource:action permissions."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class PermissionModel(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    resource = Column(String(64), nullable=False)
    action = Column(String(32), nullable=False)

    roles = relationship(
        "RoleModel",
        secondary="role_permissions",
        back_populates="permissions",
    )
