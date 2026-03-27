"""Role model — defines authorization roles (admin, operator, viewer)."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class RoleModel(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(32), nullable=False, unique=True)
    description = Column(String(256), nullable=True)

    users = relationship("UserModel", back_populates="role")
    permissions = relationship(
        "PermissionModel",
        secondary="role_permissions",
        back_populates="roles",
    )
