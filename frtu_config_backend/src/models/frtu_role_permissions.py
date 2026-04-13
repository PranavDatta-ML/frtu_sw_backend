import uuid
from sqlalchemy import Column, DateTime, PrimaryKeyConstraint, String, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from src.core.db import Base, ModelAdmin
from sqlalchemy.orm import relationship

class FRTURolePermissions(Base, ModelAdmin):
    __tablename__ = "frtu_role_permissions"
    __bind_key__ = "public"
    __table_args__ = (
        PrimaryKeyConstraint("role_id", "permission_id", name="frtu_role_permissions_pk"),
        {"schema": "public"}
    )

    # id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("public.frtu_roles.id"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("public.frtu_permissions.id"), nullable=False)
    creation_time = Column(TIMESTAMP, nullable=True)
    last_update_time = Column(TIMESTAMP, nullable=True)
    
    role = relationship("FRTURoles", back_populates="role_permissions")
    permission = relationship("FRTUPermissions", back_populates="role_permissions")
