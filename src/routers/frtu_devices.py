from uuid import UUID
from fastapi import APIRouter, Header, Request, Depends
from src import Settings
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_devices import FRTUDeviceCreate
from src.utils.jwt_tokens import decode_access_token
from src.views.frtu_devices import create_device, delete_device, read_devices, update_device

router = APIRouter(
    prefix="/device",
    tags=['frtu_devices']
)

@router.post("/create")
async def api_create_device(
    data: FRTUDeviceCreate,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "DEVICES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await create_device(data=data.model_dump(), requester_id=requester_id)




@router.post("/read")
async def device_read(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await read_devices(request, authorization)

@router.post("/update")
async def device_update(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_device(request, authorization)


@router.post("/delete")
async def device_delete(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await delete_device(request, authorization)





