from fastapi import APIRouter, Header, Request, Depends

from src import Settings
from src.views.frtu_permissions import check_user_permission, create_permission, delete_permission, get_all_permissions, get_available_resources, get_user_permissions, update_permission

router = APIRouter(
    prefix="/api/permissions",
    tags=['Permissions']
)


@router.post("")
async def create_permissions(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await create_permission(request, authorization)


@router.get("")
async def get_permissions(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_all_permissions(request, authorization)

@router.get("/user")
async def get_specific_user_permissions(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_user_permissions(request, authorization)

@router.put("")
async def update_user_permissions(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_permission(request, authorization)


@router.delete("")
async def delete_user_permissions(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await delete_permission(request, authorization)



@router.get("/resources")
async def get_list_resources(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await get_available_resources(request)


@router.get("/check")
async def check_permissions(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await check_user_permission(request, authorization)


