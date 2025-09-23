from fastapi import APIRouter, Request, Depends

from src import Settings
from src.views.frtu_devices import create

router = APIRouter(
    prefix="",
    tags=['frtu']
)


@router.post("/")
async def post(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await create(request, settings)


# @router.get("/")
# async def create(request: Request, settings: Settings = Depends(Settings.get_settings)):
#     return await get(request, settings)