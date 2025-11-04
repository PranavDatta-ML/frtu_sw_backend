from fastapi import APIRouter, Header, Request, Depends

from src import Settings
from src.views.frtu_role_permissions import assign_permissions_to_role, get_all_role_permissions, get_role_permissions, remove_permissions_from_role


router = APIRouter(
    prefix="/api/role-permissions",
    tags=['Role-Permission Management']
)


@router.post("/assign")
async def assign_role_permissions(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await assign_permissions_to_role(request, authorization)


@router.delete("/remove")
async def remove_role_permissions(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await remove_permissions_from_role(request, authorization)


@router.get("/{role_name}")
async def fetch_role_permissions(request: Request, role_name: str, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_role_permissions(request, role_name, authorization)

@router.get("")
async def fetch_all_role_permissions(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_all_role_permissions(request, authorization)


