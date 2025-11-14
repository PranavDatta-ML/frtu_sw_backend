from fastapi import APIRouter, Header, Request, Depends
from src import Settings
# from src.routers.frtu_users import user_login
from src.views.frtu_tenants import create_tenant, create_tenant_user, delete_tenant, get_tenant_by_name, get_tenants, tenant_login, update_tenant  # your project create view function

router = APIRouter(
    prefix="/tenant",
    tags=['frtu_tenants']
)

@router.post("/create")
async def tenant_create(request: Request,authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await create_tenant(request, authorization)

@router.post("/user/create")
async def user_tenant_create(request: Request,authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await create_tenant_user(request, authorization)

@router.get("/get-tenants")
async def tenant_read(request: Request):
    return await get_tenants(request)

@router.get("/get-tenant")
async def tenant_read(request: Request):
    return await get_tenant_by_name(request)

@router.post("/update-tenant")
async def tenant_update(request: Request):
    return await update_tenant(request)

@router.delete("/delete-tenant")
async def tenant_delete(request: Request):
    return await delete_tenant(request)

@router.post("/login")
async def login_tenant(request: Request,authorization: str = Header(..., convert_underscores=False)):
    return await tenant_login(request)

# @router.post("/user/login")
# async def login_tenant_user(request: Request,authorization: str = Header(..., convert_underscores=False)):
#     return await user_login(request)