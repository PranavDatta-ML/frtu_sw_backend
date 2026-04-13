import uuid
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy import JSON, TIMESTAMP, Column, ForeignKey
from src.core.db import Base, ModelAdmin

class FRTUBaseConfig(Base, ModelAdmin):
    __tablename__ = "frtu_base_config"
    __bind_key__ = "public"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("public.frtu_devices.id"), nullable=False, unique=True)
    config_json = Column(JSON, nullable=False, default=dict)
    attribute = Column(JSON, default=dict)
    last_synced_at = Column(TIMESTAMP, nullable=True)
    creation_time = Column(TIMESTAMP, nullable=True)
    last_update_time = Column(TIMESTAMP, nullable=True)