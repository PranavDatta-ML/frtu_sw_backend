from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.params import Query
from src.middleware.CreatePermissionMiddleware import require_permission
from src.views.delete_hierarchy_by_admin import delete_hierarchy_by_admin_id

router = APIRouter(
    prefix="",
    tags=['frtu_auto_discover_modules_list']
)


@router.delete("/api/admin/{admin_id}/hierarchy")
async def api_delete_hierarchy(
    admin_id: UUID,
    confirm: bool = Query(False, description="Confirm complete hierarchy deletion"),
    # current_user_id: UUID = Depends(require_permission("edit", "ADMIN")),
):
    return await delete_hierarchy_by_admin_id(admin_id, confirm)

