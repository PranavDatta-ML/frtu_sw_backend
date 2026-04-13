import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, JSON, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from src.core.db import Base
from src.core.db import ModelAdmin



class FRTUSlots(Base, ModelAdmin):
    __tablename__ = "frtu_slots"
    __bind_key__ = 'public'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("public.frtu_devices.id"), nullable=False)
    name = Column(String, nullable=False)
    attribute = Column(JSON, default={})
    creation_time = Column(TIMESTAMP, nullable=True)
    last_update_time = Column(TIMESTAMP, nullable=True)




