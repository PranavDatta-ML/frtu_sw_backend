from uuid import UUID

from fastapi import Depends, Request, APIRouter

from src import Settings
from src.views.tasks import push_view
from src.views.tasks import list_view
from src.views.tasks import get_view


router = APIRouter(
    prefix="/task",
    tags=['Task']
)


@router.post("/push")
async def push(request: Request, settings: Settings = Depends(Settings.get_settings)):
    """
    Endpoint to handle the push operation.

    Args:
        request (Request): The HTTP request object containing the request data.
        settings (Settings): Configuration settings, injected via dependency injection.

    Returns:
        JSONResponse: The result of the `push_view` function, containing the processed data or status.
    """
    return await push_view(request, settings)


@router.get("/list")
async def list(request: Request, settings: Settings = Depends(Settings.get_settings)):
    """
    Endpoint to handle the push operation.

    Args:
        request (Request): The HTTP request object containing the request data.
        settings (Settings): Configuration settings, injected via dependency injection.

    Returns:
        JSONResponse: The result of the `push_view` function, containing the processed data or status.
    """
    return await list_view(request, settings)


@router.get("/get/{task_id}")
async def get(task_id: UUID, request: Request, settings: Settings = Depends(Settings.get_settings)):
    """
    Endpoint to handle the push operation.

    Args:
        request (Request): The HTTP request object containing the request data.
        settings (Settings): Configuration settings, injected via dependency injection.

    Returns:
        JSONResponse: The result of the `push_view` function, containing the processed data or status.
    """
    return await get_view(task_id, request, settings)