import uuid
from sqlalchemy import Column, DateTime, String, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from src.core.db import Base, ModelAdmin

class FRTUTenants(Base, ModelAdmin):
    __tablename__ = "frtu_tenants"
    __bind_key__ = "public"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("public.frtu_platform_admins.id"), nullable=False)
    name = Column(String, nullable=False, unique=True)
    # type = Column(String, nullable=True)
    attribute = Column(JSON, nullable=True)
    creation_time = Column(TIMESTAMP, nullable=True)
    last_update_time = Column(TIMESTAMP, nullable=True)

    # admin = relationship("FRTUPlatformAdmin", back_populates="tenants")

