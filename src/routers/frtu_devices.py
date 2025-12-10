from uuid import UUID
from fastapi import APIRouter, Header, Request, Depends
from src import Settings
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_devices import FRTUDeviceCreate, FRTUDeviceDelete, FRTUDeviceRead, FRTUDeviceUpdate
from src.utils.jwt_tokens import decode_access_token
from src.views.frtu_devices import create_device, delete_device, read_device, read_device_by_id, update_device_by_id, update_device_by_name

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


# @router.post("/read")
# async def api_read_devices(
#     data: FRTUDeviceRead,
#     authorization: str = Header(...),
#     page: int = 1,
#     limit: int = 10,
#     name: str | None = None,
#     user_id: UUID = Depends(require_permission("view", "DEVICES"))
# ):
#     token = authorization.split(" ")[1]
#     decoded = decode_access_token(token)
#     requester_id = UUID(decoded["sub"])
#     return await read_devices(
#         data=data.model_dump(),
#         requester_id=requester_id,
#         name=name,
#         page=page,
#         limit=limit
#     )

@router.post("/read/{id}")
async def api_read_device_by_id(
    id: UUID,
    data: FRTUDeviceRead,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("view", "DEVICES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await read_device_by_id(
        device_id=id,
        requester_id=requester_id,
        data=data.model_dump()
    )

# ----------- Get device details by name(partial or exact) or id -----------
@router.post("/read")
async def api_read_device(
    data: FRTUDeviceRead,
    authorization: str = Header(...),
    page: int = 1,
    limit: int = 10,
    user_id: UUID = Depends(require_permission("view", "DEVICES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await read_device(
        data=data.model_dump(),
        requester_id=requester_id,
        page=page,
        limit=limit
    )


@router.post("/update-by-name")
async def api_update_device(
    data: FRTUDeviceUpdate,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "DEVICES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await update_device_by_name(
        data=data.model_dump(),
        requester_id=requester_id
    )

@router.post("/update")
async def api_update_device(
    data: FRTUDeviceUpdate,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "DEVICES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await update_device_by_id(
        data=data.model_dump(),
        requester_id=requester_id
    )

@router.post("/delete")
async def api_delete_device(
    data: FRTUDeviceDelete,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "DEVICES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await delete_device(data=data.model_dump(), requester_id=requester_id)





