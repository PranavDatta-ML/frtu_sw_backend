from fastapi import APIRouter, Header, Query, Request, Depends
from src import Settings
from src.views.frtu_configure_di_channel import  configure_di_channel_properties, configure_di_channel_remote, configure_do_channel_properties, configure_do_channel_remote, get_all_channels_by_slot, get_di_channel_detail, get_do_channel_detail, update_di_channel_properties, update_di_channel_remote, update_do_channel_properties, update_do_channel_remote


router = APIRouter(
    prefix="",
    tags=['frtu_configure_di_channel']
)


@router.post("/configure_di_channel_remote")
async def di_channel_configuration(request: Request, frtuname, frtutype, slotnumber, channel, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await configure_di_channel_remote(request, frtuname, frtutype, slotnumber, channel, authorization)


@router.post("/configure_di_channel_properties")
async def di_channel_properties_config(request: Request, frtuname, frtutype, slotnumber, channel, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await configure_di_channel_properties(request, frtuname, frtutype, slotnumber, channel, authorization)



@router.post("/configure_do_channel_remote")
async def do_channel_configuration(request: Request, frtuname, frtutype, slotnumber, channel, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await configure_do_channel_remote(request, frtuname, frtutype, slotnumber, channel, authorization)


@router.post("/configure_do_channel_properties")
async def do_channel_properties_config(request: Request, frtuname, frtutype, slotnumber, channel, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await configure_do_channel_properties(request, frtuname, frtutype, slotnumber, channel, authorization)



@router.post("/update_di_channel_remote")
async def di_channel_config_update(request: Request, frtuname, frtutype, slotnumber, channel, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_di_channel_remote(request, frtuname, frtutype, slotnumber, channel, authorization)


@router.post("/update_di_channel_properties")
async def channel_di_properties_config_update(request: Request, frtuname, frtutype, slotnumber, channel, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_di_channel_properties(request, frtuname, frtutype, slotnumber, channel, authorization)

@router.post("/update_do_channel_remote")
async def do_channel_config_update(request: Request, frtuname, frtutype, slotnumber, channel, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_do_channel_remote(request, frtuname, frtutype, slotnumber, channel, authorization)


@router.post("/update_do_channel_properties")
async def channel_do_properties_config_update(request: Request, frtuname, frtutype, slotnumber, channel, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_do_channel_properties(request, frtuname, frtutype, slotnumber, channel, authorization)


@router.get("/get_di_channel_detail")
async def channel_di_config_detail(request: Request, frtuname, slotnumber, channel, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_di_channel_detail(request, frtuname, slotnumber, channel, authorization)


@router.get("/get_do_channel_detail")
async def channel_do_config_detail(request: Request, frtuname, slotnumber, channel, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_do_channel_detail(request, frtuname, slotnumber, channel, authorization)


@router.get("/get_all_channels_by_slot")
async def channel_do_di_config_detail(request: Request, frtuname, slotnumber,  authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_all_channels_by_slot(request, frtuname, slotnumber, authorization)





