from fastapi import APIRouter, Header, Query, Request, Depends
from src import Settings
from src.views.frtu_modules import auto_discover_modules, auto_discover_modules_msg

router = APIRouter(
    prefix="",
    tags=['frtu_modules']
)


# @router.post("/")
# async def post(request: Request, settings: Settings = Depends(Settings.get_settings)):
#     return await create(request, settings)

@router.post("/auto_discover_modules")
async def auto_discover_module(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await auto_discover_modules(request, authorization)


# @router.get("/auto_discover_modules_msg")
# async def auto_discover_modules_msg_slot(request: Request, authorization: str = Header(..., convert_underscores=False), a_name: str = Query(...), a_type: str = Query(...), settings: Settings = Depends(Settings.get_settings)):
#     return await auto_discover_modules_msg(request, authorization, a_name, a_type)

@router.get("/auto_discover_modules_msg")
async def auto_discover_modules_msg_slot(request: Request, a_name: str = Query(...), a_type: str = Query(...), settings: Settings = Depends(Settings.get_settings)):
    return await auto_discover_modules_msg(request, a_name, a_type)



