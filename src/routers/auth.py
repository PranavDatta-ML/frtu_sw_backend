from fastapi import APIRouter, Request, Depends

from src import Settings
from src.views.auth import validate

router = APIRouter(
    prefix="",
    tags=['auth']
)


@router.post("/")
async def post(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await validate(request, settings)