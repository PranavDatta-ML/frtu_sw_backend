from uuid import UUID
from fastapi import APIRouter, HTTPException, Header, Query, Request, Depends, status
from src import Settings
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_modules import AddModuleManuallyRequest, DeviceModulesSimpleResponse
from src.utils.jwt_tokens import decode_access_token
from src.views.frtu_manual_module import add_module_manually, configure_module_manually, get_device_modules_simple, get_module_list_view


router = APIRouter(
    prefix="",
    tags=['frtu_module_manual_flow']
)

@router.get("/get_module_list")
async def api_get_module_list(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )

    token = authorization.split(" ", 1)[1].strip()
    decode_access_token(token)

    return await get_module_list_view()

@router.post("/add_module_manually")
async def api_add_module_manually(
    device_id: str = Query(...),
    device_type: str = Query(),
    payload: AddModuleManuallyRequest = ...,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await add_module_manually(device_id, device_type, payload, user_id)

@router.get("/get_modules", response_model=DeviceModulesSimpleResponse)
async def api_get_device_modules(
    device_id: str = Query(...),
    device_type: str = Query(),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_device_modules_simple(device_id, device_type)

@router.post("/configure_module_manually")
async def manually_configure_module(request: Request,frtu_name, frtu_type, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await configure_module_manually(request, frtu_name, frtu_type, authorization, settings)

