import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, JSON, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from src.core.db import Base
from src.core.db import ModelAdmin

class FRTUModules(Base, ModelAdmin):
    __tablename__ = "frtu_modules"
    __bind_key__ = 'public'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slot_id = Column(UUID(as_uuid=True), ForeignKey("frtu_slots.id"), nullable=False)
    name = Column(String, nullable=False)
    # module_type = Column(String, nullable=False)  # e.g. DI, DO, PS, COM
    module_type = Column(UUID(as_uuid=True), ForeignKey("frtu_module_type.id"), nullable=False)
    description = Column(String, nullable=True)
    attribute = Column(JSON, nullable=True)
    channel = Column(JSON, nullable=True)
    creation_time = Column(TIMESTAMP, nullable=True)
    last_update_time = Column(TIMESTAMP, nullable=True)





