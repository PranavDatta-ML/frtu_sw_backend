from fastapi import APIRouter
from fastapi import Request
from fastapi import Depends

from src import Settings
from src.views.base import version_view


router = APIRouter(
    prefix="",
    tags=['Base']
)


@router.get("/version")
async def version(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await version_view(settings)