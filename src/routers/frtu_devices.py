from fastapi import APIRouter, Header, Request, Depends
from src import Settings
from src.views.frtu_devices import create_device, delete_device, read_devices, update_device

router = APIRouter(
    prefix="/device",
    tags=['frtu_devices']
)


# @router.post("/")
# async def post(request: Request, settings: Settings = Depends(Settings.get_settings)):
#     return await create(request, settings)

@router.post("/create")
async def device_create(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await create_device(request, authorization)

@router.post("/read")
async def device_read(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await read_devices(request, authorization)

@router.post("/update")
async def device_update(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_device(request, authorization)


@router.post("/delete")
async def device_delete(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await delete_device(request, authorization)





