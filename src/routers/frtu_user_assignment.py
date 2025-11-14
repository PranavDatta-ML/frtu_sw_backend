# src/routers/user_assignment.py
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from src.middleware.CreatePermissionMiddleware import require_create_permission
from src.middleware.ReadPermissionMiddleware import require_read_permission
from src.schemas.frtu_user_assignment import FRTUUserAssignmentCreate, FRTUUserAssignmentRead
from src.views.frtu_user_assignment import assign_role_to_user, list_user_assignments, remove_user_assignment

router = APIRouter(prefix="/api/user-assignments", tags=["user-assignments"])

@router.post("/", response_model=FRTUUserAssignmentRead)
async def api_assign_user(
    payload: FRTUUserAssignmentCreate,
    assigned_by: UUID = Depends(require_create_permission),   # returns UUID
):
    """
    Assign role to a user. `require_create_permission` will validate caller token.
    """
    result = await assign_role_to_user(payload.dict(), assigned_by)
    return result

@router.get("/by-user/{user_id}", response_model=list[FRTUUserAssignmentRead])
async def api_list_user_assignments(
    user_id: UUID,
    _ = Depends(require_read_permission)  # validate caller has read permission
):
    return await list_user_assignments(user_id)

@router.delete("/")
async def api_delete_assignment(
    user_id: UUID,
    role_id: UUID,
    scope_type: str = None,
    scope_id: UUID | None = None,
    _ = Depends(require_create_permission)   # require permission to 修改 assignments
):
    deleted = await remove_user_assignment(user_id, role_id, scope_type, scope_id)
    return {"deleted": deleted}
