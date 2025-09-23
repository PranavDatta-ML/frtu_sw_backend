import json
from uuid import UUID

from fastapi import Request

from src import HttpStatusCode
from src import Settings
from src.utils.schema import verify_schema
from src.schemas.list import ListQueryParamSchema
from src.models.tasks import ScheduledTasksMaster
from src.models.tasks import HTTPConfig
from src.models.tasks import ScheduledTasksIteration

async def push_view(request: Request, settings: Settings):
    pass

async def list_view(request: Request, settings: Settings):
   pass

async def get_view(task_id: UUID, request: Request, settings: Settings):
    pass