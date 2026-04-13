import uuid

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import Float
from sqlalchemy import TIMESTAMP
from sqlalchemy import JSON
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Enum

from src.core.db import Base
from src.core.db import ModelAdmin

from src.enums.http import HTTPMethods


class ScheduledTasksMaster(Base, ModelAdmin):
    __tablename__ = 'scheduled_tasks_master'
    __bind_key__ = 'public'

    def get_default_log_config(self):
        return {'enabled': True, 'duration': -1}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    external_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    protocol = Column(String(10), nullable=False)
    timeout = Column(Integer, nullable=False, default=60)
    custom_start_ts = Column(TIMESTAMP(timezone=True), nullable=False)
    log = Column(JSON, nullable=False, default=get_default_log_config)
    interval = Column(JSON, nullable=False, default=lambda: [60])  # Stores an array of positive integers in seconds

    scheduled_task_iterations = relationship('ScheduledTasksIteration', back_populates='scheduled_tasks_master')
    http_config = relationship('HTTPConfig', back_populates='scheduled_tasks_master')

    def __repr__(self):
        return f'<ScheduledTasksMaster(id={self.id}, external_id={self.external_id}, protocol={self.protocol})>'


class ScheduledTasksIteration(Base, ModelAdmin):
    __tablename__ = 'scheduled_task_iterations'
    __bind_key__ = 'public'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey('scheduled_tasks_master.id', ondelete='CASCADE'), nullable=False)
    sequence = Column(Integer, nullable=False)
    start_at = Column(TIMESTAMP(timezone=True), nullable=False)
    end_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resp_code = Column(Integer, nullable=True)
    succ_response = Column(JSON, nullable=True)
    err_response = Column(JSON, nullable=True)
    response_time = Column(Float, nullable=True)  # In seconds
    traceback = Column(Text, nullable=True)
    traceback_line_no = Column(Integer, nullable=True)

    scheduled_tasks_master = relationship("ScheduledTasksMaster", back_populates="scheduled_task_iterations")

    def __repr__(self):
        return f'<ScheduledTasksIteration(id={self.id}, task_id={self.task_id}, sequence={self.sequence}>'


class HTTPConfig(Base, ModelAdmin):
    __tablename__ = 'http_config'
    __bind_key__ = 'public'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey('scheduled_tasks_master.id', ondelete='CASCADE'), nullable=False)
    endpoint = Column(String, nullable=False)
    method = Column(Enum(HTTPMethods), nullable=False)
    body = Column(JSON, nullable=True)
    header = Column(JSON, nullable=True)

    scheduled_tasks_master = relationship('ScheduledTasksMaster', back_populates='http_config')

    def __repr__(self):
        return f'<HTTPConfig(id={self.id}, task_id={self.task_id})>'