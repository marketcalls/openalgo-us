from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    role = relationship("Role", back_populates="users")

    def is_superadmin(self):
        return self.role.name == "superadmin"

    def is_admin(self):
        return self.role.name in ["superadmin", "admin"]

class AuthSettings(Base):
    __tablename__ = "auth_settings"

    id = Column(Integer, primary_key=True, index=True)
    regular_auth_enabled = Column(Boolean, default=True)
    google_auth_enabled = Column(Boolean, default=False)
    google_client_id = Column(String, nullable=True)
    google_client_secret = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"))
