from uuid import UUID
from fastapi import APIRouter, HTTPException, Header, Query, Request, Depends, status
from src import Settings
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_manual_module import ConfigureModuleManuallyRequest, GetConfiguredModuleResponse
from src.schemas.frtu_modules import AddModuleAutoRequest, AddModuleManuallyRequest, DeviceModulesResponse
from src.utils.jwt_tokens import decode_access_token
from src.views.frtu_manual_module import add_module, add_module_manually, configure_module_manually, get_configured_module, get_device_modules, get_module_list_view


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

@router.post("/add_module")
async def api_add_module_auto(
    payload: AddModuleAutoRequest,
    device_id: str = Query(...),
    device_type: str = Query("FRTU"),
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await add_module(device_id, device_type, payload, user_id)

# ----------------------------- Payload like module_id,module_type and slot_id ---
@router.post("/add_module_manually")
async def api_add_module_manually(
    device_id: str = Query(...),
    device_type: str = Query(),
    payload: AddModuleManuallyRequest = ...,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await add_module_manually(device_id, device_type, payload, user_id)

@router.get("/get_modules", response_model=DeviceModulesResponse)
async def api_get_device_modules(
    device_id: str = Query(...),
    device_type: str = Query(...),
    is_auto: bool | None = Query(default=None),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_device_modules(device_id, device_type, is_auto)

@router.post("/configure_module_manually")
async def api_configure_module_manually(
    payload: ConfigureModuleManuallyRequest,
    device_id: str = Query(...),
    device_type: str = Query("FRTU"),
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await configure_module_manually(device_id, device_type, payload, user_id)

# router
@router.get("/configured_module_detail", response_model=GetConfiguredModuleResponse)
async def api_get_configured_module(
    module_id: UUID = Query(...),
    device_id: str = Query(...),
    device_type: str = Query("FRTU"),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_configured_module(device_id, device_type, module_id)


