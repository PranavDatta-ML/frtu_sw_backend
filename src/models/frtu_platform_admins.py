import uuid

from sqlalchemy import Column, PrimaryKeyConstraint, UniqueConstraint, func
from sqlalchemy import String
from sqlalchemy import TIMESTAMP
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID


from src.core.db import Base
from src.core.db import ModelAdmin

class FRTUPlatformAdmin(Base, ModelAdmin):
    __tablename__ = 'frtu_platform_admins'
    __bind_key__ = 'public'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='frtu_platform_admins_pkey'),
        UniqueConstraint('email', name='platform_admin_unique_email'),
        UniqueConstraint('mobile_no', name='platform_admin_unique_mobile_no'),
        {'schema': 'public'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    mobile_no = Column(String, nullable=False)
    email = Column(String, nullable=True)
    attribute = Column(JSON, nullable=True)
    creation_time = Column(TIMESTAMP, nullable=True, server_default=func.now())
    last_update_time = Column(TIMESTAMP, nullable=True, onupdate=func.now())