
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from src.middleware.CreatePermissionMiddleware import require_create_permission, require_permission
from src.middleware.ReadPermissionMiddleware import require_read_permission
from src.schemas.frtu_user_assignment import FRTUUserAssignmentCreate, FRTUUserAssignmentRead, FRTUUserAssignmentUpdate
from src.views.frtu_user_assignment import assign_role_to_user, delete_user_assignment, get_user_assignment, list_user_assignments, update_user_assignment

router = APIRouter(
    prefix="/api/user-assignments", 
    tags=["user-assignments"]
)


# @router.post("/", response_model=FRTUUserAssignmentRead)
# async def api_assign_user(payload: FRTUUserAssignmentCreate, assigned_by: UUID = Depends(require_permission("edit", "USER_ASSIGNMENT"))):
#     result = await assign_role_to_user(payload.dict(), assigned_by)
#     return result


@router.post("/", response_model=FRTUUserAssignmentRead)
async def api_assign_user(
    payload: FRTUUserAssignmentCreate,
    assigned_by = Depends(require_permission("edit", "USER_ASSIGNMENT"))
):
    return await assign_role_to_user(payload.dict(), assigned_by)

# READ ALL ASSIGNMENTS OF USER
@router.get("/user/{user_id}", response_model=list[FRTUUserAssignmentRead])
async def api_list_assignments(user_id: UUID, user: UUID = Depends(require_permission("view", "USER_ASSIGNMENT"))):
    return await list_user_assignments(user_id)


# READ SINGLE ASSIGNMENT
@router.get("/{assignment_id}", response_model=FRTUUserAssignmentRead)
async def api_get_assignment(assignment_id: UUID,user: UUID = Depends(require_permission("view", "USER_ASSIGNMENT"))):
    return await get_user_assignment(assignment_id)


# UPDATE ASSIGNMENT
@router.put("/{assignment_id}", response_model=FRTUUserAssignmentRead)
async def api_update_assignment(assignment_id: UUID,payload: FRTUUserAssignmentUpdate,updated_by: UUID = Depends(require_permission("edit", "USER_ASSIGNMENT"))):
    return await update_user_assignment(assignment_id, payload, updated_by)


# DELETE ASSIGNMENT
@router.delete("/{assignment_id}")
async def api_delete_assignment(assignment_id: UUID,user: UUID = Depends(require_permission("edit", "USER_ASSIGNMENT"))):
    return await delete_user_assignment(assignment_id)