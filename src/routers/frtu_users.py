from fastapi import APIRouter, Request, Depends
from src import Settings
from src.views.frtu_users import create_user, get_users, login_user

router = APIRouter(
    prefix="/user",
    tags=['frtu_users']
)

@router.post("/create")
async def user_create(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await create_user(request, settings)

@router.post("/login")
async def user_login(request: Request):
    return await login_user(request)

@router.get("")
async def user_list(request: Request):
    return await get_users(request)

# @router.post("/update")
# async def user_update(request: Request):
#     return await update_user(request)