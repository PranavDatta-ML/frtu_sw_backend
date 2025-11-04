from fastapi import APIRouter, Header, Request, Depends

from src import Settings
from src.views.frtu_roles import create_role, get_all_roles,get_role_by_name,update_role_by_name,delete_role_by_name,get_role_users

router = APIRouter(
    prefix="/api/roles",
    tags=['Roles']
)


@router.post("")
async def create_roles(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await create_role(request, authorization, settings)


@router.get("")
async def get_list_roles(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await get_all_roles(request)

@router.get("/")
async def get_role(request: Request,name:str, settings: Settings = Depends(Settings.get_settings)):
    return await get_role_by_name(request, name=name)

@router.put("/")
async def update_role(request: Request, name:str, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_role_by_name(request, name=name, authorization=authorization)

# @router.put("/update/{name}")
# async def update_role(request: Request, name:str, authorization: str = Header(...), settings: Settings = Depends(Settings.get_settings)):
#     return await update_role_by_name(request, name=name, authorization)

@router.delete("/")
async def delete_role(request: Request, name:str, authorization: str = Header(...), settings: Settings = Depends(Settings.get_settings)):
    return await delete_role_by_name(request, name=name, authorization=authorization)

@router.get("/users")
async def get_user_using_role_name(request: Request, name:str, settings: Settings = Depends(Settings.get_settings)):
    return await get_role_users(request, name=name)

