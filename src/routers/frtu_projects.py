from uuid import UUID
from fastapi import APIRouter, Body, Header, Request, Depends
from src import Settings
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_projects import FRTUProjectCreate, FRTUProjectDelete, FRTUProjectDeleteByID, FRTUProjectRead, FRTUProjectUpdateById, FRTUProjectUpdateByName
from src.utils.jwt_tokens import decode_access_token
from src.views.frtu_projects import create_project, delete_project_by_id, delete_project_by_name, read_project_by_id, read_projects, update_project_by_id, update_project_by_name  # your project create view function

router = APIRouter(
    prefix="/project",
    tags=['frtu_projects']
)

@router.post("/create")
async def api_create_project(data: FRTUProjectCreate,authorization: str = Header(...),user_id: UUID = Depends(require_permission("edit", "PROJECT"))):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    creator_id = UUID(decoded["sub"])

    return await create_project(data.model_dump(), creator_id)



@router.post("/read")
async def api_read_projects(data: dict | None = Body(default=None),authorization: str = Header(...),page: int = 1,limit: int = 10,name: str | None = None,tenant_id: UUID | None = None,user_id: UUID = Depends(require_permission("view", "PROJECT"))):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])

    payload_name = None
    if data:
        entity = data.get("entity")
        if entity and isinstance(entity, dict):
            payload_name = entity.get("name")

    final_name = name or payload_name

    return await read_projects(user_id=requester_id,tenant_id=tenant_id,search=final_name,page=page,limit=limit)

@router.post("/read/id={project_id}")
async def api_read_project_by_id(project_id: UUID,data: dict = Body(...),authorization: str = Header(...),user_id: UUID = Depends(require_permission("view", "PROJECT"))):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])

    return await read_project_by_id(project_id, requester_id)


@router.post("/update")
async def api_update_project_by_name(data: dict,authorization: str = Header(...),user_id: UUID = Depends(require_permission("edit", "PROJECT"))):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await update_project_by_name(data, requester_id)


@router.post("/update/{project_id}")
async def api_update_project_by_id(project_id: UUID,data: FRTUProjectUpdateById,authorization: str = Header(...),user_id: UUID = Depends(require_permission("edit", "PROJECT"))):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])

    return await update_project_by_id(project_id, data.model_dump(), requester_id)


@router.post("/delete")
async def api_delete_project_by_name(data: FRTUProjectDelete,authorization: str = Header(...),user_id: UUID = Depends(require_permission("edit", "PROJECT"))):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])

    return await delete_project_by_name(data, requester_id)


@router.post("/delete/id={project_id}")
async def api_delete_project_by_id(data: FRTUProjectDeleteByID,authorization: str = Header(...),user_id: UUID = Depends(require_permission("edit", "PROJECT"))):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await delete_project_by_id(data, requester_id)


