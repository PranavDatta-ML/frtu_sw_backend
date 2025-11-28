from uuid import UUID
from fastapi import APIRouter, Header, Request, Depends
from src import Settings
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_sites import FRTUSiteCreate, FRTUSiteRead, FRTUSiteUpdate
from src.utils.jwt_tokens import decode_access_token
from src.views.frtu_sites import create_site, delete_site,  delete_site_by_name, read_site_by_id, read_sites, update_site, update_site_by_id, update_site_by_name

router = APIRouter(
    prefix="/site",
    tags=["frtu_sites"]
)

@router.post("/create")
async def api_create_site(
    data: FRTUSiteCreate,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "SITES"))
):

    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])

    return await create_site(data.model_dump(), requester_id)

@router.post("/read")
async def api_read_sites(
    data: FRTUSiteRead,
    authorization: str = Header(...),
    name: str | None = None,
    page: int = 1,
    limit: int = 10,
    user_id: UUID = Depends(require_permission("view", "SITES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])

    return await read_sites(
        data=data.model_dump(),
        requester_id=requester_id,
        name=name,
        page=page,
        limit=limit
    )


@router.post("/read/{id}")
async def api_read_site_by_id(
    id: UUID,
    data: FRTUSiteRead,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("view", "SITES"))
):

    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])

    return await read_site_by_id(
        site_id=id,
        requester_id=requester_id,
        data=data.model_dump()
    )

@router.post("/update")
async def api_update_site(
    data: FRTUSiteUpdate,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "SITES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await update_site(data=data.model_dump(), requester_id=requester_id)


@router.post("/update-by-name")
async def api_update_site(
    data: FRTUSiteUpdate,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "SITES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])

    return await update_site_by_name(
        data=data.model_dump(),
        requester_id=requester_id
    )


@router.post("/update-by-id")
async def api_update_site_by_id(
    data: FRTUSiteUpdate,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "SITES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await update_site_by_id(
        data=data.model_dump(),
        requester_id=requester_id
    )


@router.post("/delete-by-name")
async def api_delete_site(
    data: FRTUSiteRead,    # same schema or create FRTUSiteDelete
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "SITES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await delete_site_by_name(data=data.model_dump(), requester_id=requester_id)

@router.post("/delete")
async def api_delete_site(
    data: FRTUSiteRead,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "SITES"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await delete_site(data=data.model_dump(), requester_id=requester_id)

