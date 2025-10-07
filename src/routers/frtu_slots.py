from fastapi import APIRouter, Header, Request, Depends
from src import Settings
from src.views.frtu_slots import read_slots

router = APIRouter(
    prefix="",
    tags=['frtu_slots']
)

@router.get("/slots")
async def slot_read(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await read_slots(request, authorization)






