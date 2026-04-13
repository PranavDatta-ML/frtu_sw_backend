import uuid

from sqlalchemy import Column, PrimaryKeyConstraint, UniqueConstraint, func
from sqlalchemy import String
from sqlalchemy import TIMESTAMP
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID


from src.core.db import Base, ModelAdmin

class FRTUEntities(Base, ModelAdmin):
    __tablename__ = 'frtu_entities'
    __bind_key__ = 'public'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), nullable=True)  # Reference to Platform Admin / Tenant / etc.
    name = Column(String, nullable=False)
    email_id = Column(String, nullable=False)
    mobile_no = Column(String, nullable=True)
    attribute = Column(JSON, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    creation_time = Column(TIMESTAMP, nullable=True)
    last_update_time = Column(TIMESTAMP, nullable=True)


    