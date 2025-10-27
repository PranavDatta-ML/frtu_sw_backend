from fastapi import APIRouter, Header, Query, Request, Depends
from src import Settings
from src.views.frtu_modules import auto_discover_modules_list

router = APIRouter(
    prefix="",
    tags=['frtu_auto_discover_modules_list']
)

@router.get("/auto_discover_modules")
async def auto_discover_modules(request: Request, authorization: str = Header(..., convert_underscores=False), a_name: str = Query(...), a_type: str = Query(...), settings: Settings = Depends(Settings.get_settings)):
    return await auto_discover_modules_list(request, authorization, a_name, a_type)

