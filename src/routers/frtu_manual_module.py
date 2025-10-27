from fastapi import APIRouter, Header, Query, Request, Depends
from src import Settings
from src.views.frtu_manual_module import add_module_manually, configure_module_manually


router = APIRouter(
    prefix="",
    tags=['frtu_module_manual_flow']
)


@router.post("/add_module_manually")
async def manually_add_module(request: Request,frtu_name, frtu_type, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await add_module_manually(request, frtu_name, frtu_type, authorization, settings)

@router.post("/configure_module_manually")
async def manually_configure_module(request: Request,frtu_name, frtu_type, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await configure_module_manually(request, frtu_name, frtu_type, authorization, settings)

