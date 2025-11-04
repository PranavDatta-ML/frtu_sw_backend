import uuid
from sqlalchemy import Column, String, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import UUID
from src.core.db import Base, ModelAdmin

class FRTUResources(Base, ModelAdmin):
    __tablename__ = "frtu_resources"
    __bind_key__ = "public"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    attribute = Column(JSON, nullable=True)
    creation_time = Column(TIMESTAMP, nullable=True)
    last_update_time = Column(TIMESTAMP, nullable=True)