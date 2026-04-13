import uuid

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import TIMESTAMP
from sqlalchemy import JSON
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum

from src.core.db import Base
from src.core.db import ModelAdmin
from src.enums.FrtuDeviceType import FrtuDeviceType

class FRTUDevices(Base, ModelAdmin):
    __tablename__ = 'frtu_devices'
    __bind_key__ = 'public'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey('public.frtu_sites.id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(
        Enum(FrtuDeviceType, name='frtu_device_type_enum', native_enum=True, create_type=False),
        nullable=False
    )
    attribute = Column(JSON, nullable=True)
    creation_time = Column(TIMESTAMP, nullable=True)
    last_update_time = Column(TIMESTAMP, nullable=True)


# class FRTUDevices(Base, ModelAdmin):
#     __tablename__ = 'frtu_devices'
#     __bind_key__ = 'public'

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
#     site_id = Column(UUID(as_uuid=True), ForeignKey('public.frtu_sites.id'), nullable=False)
#     name = Column(String, nullable=False)
#     type = Column(Enum(name='frtu_device_type_enum'), nullable=False)
#     attribute = Column(JSON, nullable=True)
#     creation_time = Column(TIMESTAMP, nullable=True)
#     last_update_time = Column(TIMESTAMP, nullable=True)
