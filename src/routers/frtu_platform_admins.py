from fastapi import APIRouter, Request, Depends

from src import Settings
from src.views.frtu_platform_admins import admin_login, create, delete_admin, get_admin, update_admin

router = APIRouter(
    prefix="",
    tags=['frtu_platform_admin']
)


@router.post("/api/admin")
async def post(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await create(request, settings)

@router.get("/api/admin")
async def get(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await get_admin(request)

@router.post("/api/admin/update")
async def post(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await update_admin(request)

@router.delete("/api/admin/delete")
async def delete(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await delete_admin(request)

@router.post("/admin/login")
async def login(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await admin_login(request)

