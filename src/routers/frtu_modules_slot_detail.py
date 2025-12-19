from uuid import UUID
from fastapi import APIRouter, Header, Query, Request, Depends
from src import Settings
from src.middleware.CreatePermissionMiddleware import require_permission
from src.views.frtu_modules_slot_detail import get_available_slots, get_card_type, get_slot_module_detail, get_slot_module_options, update_module_detail

router = APIRouter(
    prefix="",
    tags=['frtu_modules_detail_by_slot']
)

@router.get("/get_card_type")
async def api_get_card_type(
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_card_type()

@router.get("/get_slot_module_detail")
async def get_module_detail_by_slot(request: Request, frtuname, frtutype, slotnumber, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_slot_module_detail(request, frtuname, frtutype, slotnumber, authorization)

@router.get("/get_available_slots")
async def api_get_available_slots(
    is_available: bool = Query(...),
    device_id: UUID = Query(...),
    device_type: str = Query(...),
    user_id: UUID = Depends(require_permission("view", "SLOTS")),
):
    return await get_available_slots(
        device_id=device_id,
        device_type=device_type,
        is_available=is_available,
    )


@router.get("/get_slot_module_options")
async def get_slot_category_type_options(request: Request,frtuname, frtutype, slotnumber, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_slot_module_options(request,frtuname, frtutype, slotnumber, authorization)


@router.post("/update_module_detail")
async def get_slot_category_type_options(request: Request,frtu_name, frtu_type, slotnumber, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_module_detail(request,frtu_name, frtu_type, slotnumber, authorization)

