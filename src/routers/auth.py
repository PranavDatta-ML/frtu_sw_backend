from fastapi import APIRouter, Request, Depends

from src import Settings

router = APIRouter(
    prefix="/auth",
    tags=['auth']
)


@router.post("/login")
async def login_post(request: Request, settings: Settings = Depends(Settings.get_settings)):
    pass