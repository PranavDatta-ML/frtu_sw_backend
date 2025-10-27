from fastapi import APIRouter, Header, Query, Request, Depends
from src import Settings
from src.views.frtu_modules_slot_detail import get_available_slots, get_card_type, get_slot_module_detail, get_slot_module_options, update_module_detail

router = APIRouter(
    prefix="",
    tags=['frtu_modules_detail_by_slot']
)


@router.get("/get_slot_module_detail")
async def get_module_detail_by_slot(request: Request, frtuname, frtutype, slotnumber, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_slot_module_detail(request, frtuname, frtutype, slotnumber, authorization)

@router.get("/get_available_slots")
async def get_empty_slots(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_available_slots(request, authorization)


@router.get("/get_slot_module_options")
async def get_slot_category_type_options(request: Request,frtuname, frtutype, slotnumber, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_slot_module_options(request,frtuname, frtutype, slotnumber, authorization)

@router.get("/get_card_type")
async def get_module_type_options(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_card_type(request, authorization)


@router.post("/update_module_detail")
async def get_slot_category_type_options(request: Request,frtu_name, frtu_type, slotnumber, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_module_detail(request,frtu_name, frtu_type, slotnumber, authorization)

