from fastapi import APIRouter, Header, Request, Depends
from src import Settings
from src.views.frtu_sites import create_site, delete_site, read_sites, update_site

router = APIRouter(
    prefix="/site",
    tags=["frtu_sites"]
)

@router.post("/create")
async def site_create(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await create_site(request, authorization, settings)

@router.post("/read")
async def site_read(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await read_sites(request, authorization, settings)

@router.post("/update")
async def site_update(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_site(request, authorization, settings)

@router.post("/delete")
async def site_delete(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await delete_site(request, authorization, settings)


# @router.post("/create")
# async def site_create(request: Request, settings: Settings = Depends(Settings.get_settings), authorization: str = Header(..., convert_underscores=False)):
#     return await create_site(request, settings, authorization)

# @router.post("/read")
# async def site_read(request: Request, settings: Settings = Depends(Settings.get_settings)):
#     return await read_sites(request)

# @router.post("/update")
# async def site_update(request: Request, settings: Settings = Depends(Settings.get_settings)):
#     return await update_site(request)

# @router.post("/delete")
# async def site_delete(request: Request, settings: Settings = Depends(Settings.get_settings)):
#     return await delete_site(request)
