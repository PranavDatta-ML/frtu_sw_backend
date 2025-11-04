from fastapi import APIRouter, Header, Request, Depends

from src import Settings
from src.views.frtu_user_assignment import assign_role_to_user, get_all_user_assignments, get_user_assignments, remove_role_from_user


router = APIRouter(
    prefix="/api/user-assignment",
    tags=['User-Assignment Management']
)


@router.post("/assign")
async def assign_user_role(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await assign_role_to_user(request, authorization)


@router.get("/{user_name}")
async def fetch_user_assignments(request: Request, user_name:str, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_user_assignments(request,user_name, authorization)


@router.delete("/remove/{assignment_id}")
async def user_role_remove(request: Request, assignment_id:str, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await remove_role_from_user(request, assignment_id, authorization)


@router.get("")
async def fetch_all_user_assignments(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):
    return await get_all_user_assignments(request, authorization)

