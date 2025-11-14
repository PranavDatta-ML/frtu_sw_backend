from fastapi import APIRouter, Request, Depends

from src import Settings
from src.views.auth import validate

router = APIRouter(
    prefix="/auth",
    tags=['auth']
)


@router.post("/login")
async def login_post(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await validate(request, settings)