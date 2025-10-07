from fastapi import APIRouter, Header, Request, Depends
from src import Settings
from src.views.frtu_projects import create_project, delete_project, read_projects, update_project  # your project create view function

router = APIRouter(
    prefix="/project",
    tags=['frtu_projects']
)

@router.post("/create")
async def project_create(request: Request, settings: Settings = Depends(Settings.get_settings), authorization: str = Header(..., convert_underscores=False)):
    return await create_project(request, settings, authorization)

@router.post("/read")
async def project_read(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await read_projects(request, authorization)

@router.post("/update")
async def project_update(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await update_project(request, authorization)

@router.post("/delete")
async def project_delete(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await delete_project(request, authorization, settings)



