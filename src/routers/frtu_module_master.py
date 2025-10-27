from fastapi import APIRouter, Header, Query, Request, Depends
from src import Settings
from src.views.frtu_modules_bkp import get_module_list
router = APIRouter(
    prefix="",
    tags=['frtu_module_master']
)

@router.get("/get_module_list")
async def auto_module_master_list(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_module_list(request, authorization)
