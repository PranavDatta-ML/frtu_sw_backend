import json
from uuid import UUID

from fastapi import Request
from src import Settings

async def push_view(request: Request, settings: Settings):
    pass

async def list_view(request: Request, settings: Settings):
   pass

async def get_view(task_id: UUID, request: Request, settings: Settings):
    pass