import uuid
from sqlalchemy import Column, DateTime, String, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from src.core.db import Base, ModelAdmin
from sqlalchemy.orm import relationship

class FRTUUserAssignment(Base, ModelAdmin):
    __tablename__ = "frtu_user_assignment"
    __bind_key__ = "public"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.frtu_users.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("public.frtu_roles.id"), nullable=False)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("public.frtu_platform_admins.id"), nullable=False)
    scope_id = Column(UUID(as_uuid=True), nullable=True)
    scope_type = Column(String, nullable=True)
    attribute = Column(JSON, nullable=True)
    creation_time = Column(TIMESTAMP, nullable=True)
    last_update_time = Column(TIMESTAMP, nullable=True)
    
    user = relationship("FRTUUsers", back_populates="assignments")
    role = relationship("FRTURoles", back_populates="user_assignments")
