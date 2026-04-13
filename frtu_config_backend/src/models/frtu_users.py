import uuid
from sqlalchemy import Column, PrimaryKeyConstraint, String, Boolean, TIMESTAMP, JSON, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from src.core.db import Base, ModelAdmin

# class FRTUUsers(Base, ModelAdmin):
#     __tablename__ = "frtu_users"
#     __bind_key__ = "public"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     email = Column(String, nullable=False, unique=True)
#     mobile_no = Column(String, nullable=False, unique=True)
#     name = Column(String, nullable=False)
#     password_hash = Column(String, nullable=False)
#     salt = Column(String, nullable=False)
#     is_active = Column(Boolean, default=True, nullable=False)
#     is_deleted = Column(Boolean, default=False, nullable=False)
#     attribute = Column(JSON, nullable=True)
#     creation_time = Column(TIMESTAMP, nullable=True)
#     last_update_time = Column(TIMESTAMP, nullable=True)

# import uuid

# from sqlalchemy import Column, PrimaryKeyConstraint, UniqueConstraint, func, Boolean
# from sqlalchemy import String
# from sqlalchemy import JSON
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy import TIMESTAMP

# from src.core.db import Base
# from src.core.db import ModelAdmin
from sqlalchemy.orm import relationship

class FRTUUsers(Base, ModelAdmin):
    __tablename__ = "frtu_users"
    __bind_key__ = "public"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="frtu_users_pk"),
        UniqueConstraint("email", name="frtu_users_unique_email"),
        UniqueConstraint("mobile_no", name="frtu_users_unique_mobile_no"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    email = Column(String, nullable=False)
    mobile_no = Column(String, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    attribute = Column(JSON, nullable=True)
    creation_time = Column(TIMESTAMP, nullable=True, server_default=func.now())
    last_update_time = Column(TIMESTAMP, nullable=True, onupdate=func.now())
    # user_type = Column(String, nullable=False, default='regular_user')


    roles = relationship("FRTURoles", back_populates="user", cascade="all, delete-orphan")
    permissions = relationship("FRTUPermissions", back_populates="user", cascade="all, delete-orphan")
    assignments = relationship("FRTUUserAssignment", back_populates="user", cascade="all, delete-orphan")
    # assignments = relationship("FRTUUserAssignment", back_populates="user", cascade="all, delete-orphan")
