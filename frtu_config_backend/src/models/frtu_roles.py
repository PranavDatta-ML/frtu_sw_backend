import uuid
from sqlalchemy import Column, DateTime, String, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from src.core.db import Base, ModelAdmin
from sqlalchemy.orm import relationship

class FRTURoles(Base, ModelAdmin):
    __tablename__ = "frtu_roles"
    __bind_key__ = "public"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.frtu_users.id"), nullable=False)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    # type = Column(String, nullable=True)
    attribute = Column(JSON, nullable=True)
    creation_time = Column(TIMESTAMP, nullable=True)
    last_update_time = Column(TIMESTAMP, nullable=True)
    
    user = relationship("FRTUUsers", back_populates="roles")
    user_assignments = relationship("FRTUUserAssignment", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship("FRTURolePermissions", back_populates="role", cascade="all, delete-orphan")
