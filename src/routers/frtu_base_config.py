from uuid import UUID
from fastapi import APIRouter, Depends, Query
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_base_config import BaseConfigPayload
from src.views.frtu_base_config import add_or_update_base_config, get_base_config


router = APIRouter(
    prefix="/device",
    tags=['frtu_device_base_config']
)


@router.post("/configure_base_config")
async def api_add_or_update_base_config(
    device_id: str = Query(...),
    payload: BaseConfigPayload = ...,
    user_id: UUID = Depends(require_permission("edit", "DEVICES")),
):
    return await add_or_update_base_config(device_id, payload, user_id)


@router.get("/get_configred_base_config")
async def api_get_base_config(
    device_id: str = Query(...),
    user_id: UUID = Depends(require_permission("view", "DEVICES")),
):
    return await get_base_config(device_id, user_id)