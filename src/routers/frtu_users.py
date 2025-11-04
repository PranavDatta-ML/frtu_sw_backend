from fastapi import APIRouter, Header, Request, Depends
from src import Settings
from src.views.frtu_users import create_user, get_users, login_user,get_user_by_name,update_user_by_name,delete_user_by_name,get_user_with_roles_permissions

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

@router.get("/by-name")
async def user_by_name(request: Request, name: str):
    return await get_user_by_name(request, name=name)

@router.get("/detail")
async def user_detail(request: Request, name: str):
    return await get_user_with_roles_permissions(request, name=name)

@router.put("/update")
async def user_update_by_name(request: Request, name: str, authorization: str = Header(..., convert_underscores=False)):
    return await update_user_by_name(request, name=name, authorization=authorization)

@router.delete("/delete")
async def user_delete_by_name(request: Request, name: str, authorization: str = Header(..., convert_underscores=False)):
    return await delete_user_by_name(request, name=name, authorization=authorization)

# @router.post("/update")
# async def user_update(request: Request):
#     return await update_user(request)