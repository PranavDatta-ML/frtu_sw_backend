from fastapi import APIRouter, Header, Request, Depends

from src import Settings
from src.routers.frtu_users import user_login
from src.views.frtu_platform_admins import  create, create_platform_admin, delete_admin, get_admin, update_admin

router = APIRouter(
    prefix="/api/admin",
    tags=['frtu_platform_admin']
)


@router.post("")
async def post(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await create(request, settings)

@router.post("/platform/create")
async def post(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await create_platform_admin(request, authorization)

@router.get("")
async def get(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await get_admin(request)

@router.post("/update")
async def post(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await update_admin(request)

@router.delete("/delete")
async def delete(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await delete_admin(request)

# @router.post("/platform-admin/login")
# async def login(request: Request, settings: Settings = Depends(Settings.get_settings)):
#     return await admin_login(request)

@router.post("/login")
async def login(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await user_login(request)

