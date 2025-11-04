from fastapi import Request, Header, Depends
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_users import FRTUUsers
from src.models.frtu_roles import FRTURoles
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_tenants import FRTUTenants
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_sites import FRTUSites
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_slots import FRTUSlots
from src.models.frtu_modules import FRTUModules
from src.core.status_codes import HttpStatusCode
from src.utils.jwt_tokens import decode_access_token
from src.core.settings import Settings
from src import log
from datetime import datetime
import uuid


async def assign_role_to_user(
    request: Request,
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(message="Invalid Authorization header")

        token = authorization.split(" ")[1]
        token_payload = decode_access_token(token)
        assigner_user_id = token_payload.get("sub")

        if not assigner_user_id:
            return HttpStatusCode.UNAUTHORIZED.response(message="Invalid token")

        assigner_user_id = uuid.UUID(assigner_user_id)

        payload = await request.json()
        user_name = payload.get("user_name")
        user_id_str = payload.get("user_id")
        role_name = payload.get("role_name")
        role_id_str = payload.get("role_id")
        scope_type = payload.get("scope_type")
        scope_id_str = payload.get("scope_id")

        valid_scope_types = ["TENANT", "PROJECT", "SITE", "DEVICE", "SLOT", "MODULE"]

        if not scope_type or scope_type not in valid_scope_types:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"'scope_type' must be one of: {', '.join(valid_scope_types)}"
            )

        auto_generated_scope = False
        if scope_id_str:
            try:
                scope_id = uuid.UUID(scope_id_str)
            except (ValueError, AttributeError):
                return HttpStatusCode.BAD_REQUEST.response(message="Invalid scope_id format")
        else:
            scope_id = uuid.uuid4()
            auto_generated_scope = True

        if user_name:
            users = await FRTUUsers.select(name=user_name)
        elif user_id_str:
            users = await FRTUUsers.select(id=uuid.UUID(user_id_str))
        else:
            return HttpStatusCode.BAD_REQUEST.response(message="Either 'user_name' or 'user_id' is required")

        if not users:
            return HttpStatusCode.NOT_FOUND.response(message="User not found")

        target_user = users[0]
        target_user_id = target_user["id"]

        if role_name:
            roles = await FRTURoles.select(name=role_name)
        elif role_id_str:
            roles = await FRTURoles.select(id=uuid.UUID(role_id_str))
        else:
            return HttpStatusCode.BAD_REQUEST.response(message="Either 'role_name' or 'role_id' is required")

        if not roles:
            return HttpStatusCode.NOT_FOUND.response(message="Role not found")

        target_role = roles[0]
        target_role_id = target_role["id"]

        existing = await FRTUUserAssignment.select(
            user_id=target_user_id,
            role_id=target_role_id,
            scope_type=scope_type,
            columns=[FRTUUserAssignment.id]
        )

        if existing:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"User '{target_user['name']}' already has role '{target_role['name']}' in scope '{scope_type}'"
            )

        exclude_keys = {
            "user_name", "user_id", "role_name", "role_id", "scope_type", "scope_id"
        }
        attribute_data = {k: v for k, v in payload.items() if k not in exclude_keys}

        now = datetime.utcnow()
        assignment_id = uuid.uuid4()

        await FRTUUserAssignment.insert(
            id=assignment_id,
            user_id=target_user_id,
            role_id=target_role_id,
            scope_type=scope_type,
            scope_id=scope_id,
            attribute=attribute_data or {},
            creation_time=now,
            last_update_time=now
        )

        return HttpStatusCode.CREATED.response(
            message=f"Role '{target_role['name']}' assigned to user '{target_user['name']}' successfully",
            data={
                "assignment_id": str(assignment_id),
                "user": {
                    "id": str(target_user_id),
                    "name": target_user["name"],
                    "email": target_user.get("email")
                },
                "role": {
                    "id": str(target_role_id),
                    "name": target_role["name"],
                    "description": target_role.get("description")
                },
                "scope": {
                    "type": scope_type,
                    "id": str(scope_id),
                    "auto_generated": auto_generated_scope
                },
                "custom_attributes": attribute_data,
                "assigned_by": str(assigner_user_id),
                "assigned_at": now.isoformat()
            }
        )

    except Exception as e:
        import traceback
        log.error(f"Failed to assign role to user: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(message=f"Failed to assign role: {str(e)}")


async def get_user_assignments(
    request: Request,
    user_name: str = None,
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )
        
        token = authorization.split(" ")[1]
        token_payload = decode_access_token(token)
        
        # Get user
        user_id_str = request.query_params.get("user_id")
        target_user = None
        
        if user_name:
            users = await FRTUUsers.select(
                name=user_name,
                columns=[FRTUUsers.id, FRTUUsers.name, FRTUUsers.email, FRTUUsers.mobile_no]
            )
            if not users:
                return HttpStatusCode.NOT_FOUND.response(
                    message=f"User with name '{user_name}' not found"
                )
            target_user = users[0]
        elif user_id_str:
            try:
                user_id = uuid.UUID(user_id_str)
                users = await FRTUUsers.select(
                    id=user_id,
                    columns=[FRTUUsers.id, FRTUUsers.name, FRTUUsers.email, FRTUUsers.mobile_no]
                )
                if not users:
                    return HttpStatusCode.NOT_FOUND.response(
                        message=f"User with ID '{user_id_str}' not found"
                    )
                target_user = users[0]
            except (ValueError, AttributeError):
                return HttpStatusCode.BAD_REQUEST.response(
                    message="Invalid user_id format"
                )
        else:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Either user_name in path or user_id in query is required"
            )
        
        target_user_id = target_user["id"]
        
        assignments = await FRTUUserAssignment.select(
            user_id=target_user_id,
            columns=[
                FRTUUserAssignment.id,
                FRTUUserAssignment.role_id,
                FRTUUserAssignment.scope_type,
                FRTUUserAssignment.scope_id,
                FRTUUserAssignment.attribute,
                FRTUUserAssignment.creation_time
            ]
        )
        
        if not assignments:
            return HttpStatusCode.OK.response(
                message=f"No role assignments found for user '{target_user['name']}'",
                data={
                    "user": {
                        "id": str(target_user_id),
                        "name": target_user["name"],
                        "email": target_user["email"]
                    },
                    "assignments": [],
                    "total_count": 0
                }
            )
        
        assignments_data = []
        
        for assignment in assignments:
            roles = await FRTURoles.select(
                id=assignment["role_id"],
                columns=[FRTURoles.id, FRTURoles.name, FRTURoles.description]
            )
            
            role_info = None
            permissions_info = []
            
            if roles:
                role = roles[0]
                role_info = {
                    "id": str(role["id"]),
                    "name": role["name"],
                    "description": role.get("description")
                }
                
                role_perms = await FRTURolePermissions.select(
                    role_id=role["id"],
                    columns=[FRTURolePermissions.permission_id]
                )
                
                if role_perms:
                    for rp in role_perms:
                        perms = await FRTUPermissions.select(
                            id=rp["permission_id"],
                            columns=[FRTUPermissions.id, FRTUPermissions.attribute]
                        )
                        if perms:
                            perm = perms[0]
                            perm_attr = perm.get("attribute", {})
                            permissions_info.append({
                                "permission_id": str(perm["id"]),
                                "name": perm_attr.get("name", "Unnamed"),
                                "resources": perm_attr.get("resources", [])
                            })
            
            assignments_data.append({
                "assignment_id": str(assignment["id"]),
                "role": role_info,
                "scope": {
                    "type": assignment["scope_type"],
                    "id": str(assignment["scope_id"])
                },
                "permissions": permissions_info,
                "assigned_at": assignment["creation_time"].isoformat() if assignment.get("creation_time") else None
            })
        
        return HttpStatusCode.OK.response(
            message=f"Assignments for user '{target_user['name']}' retrieved successfully",
            data={
                "user": {
                    "id": str(target_user_id),
                    "name": target_user["name"],
                    "email": target_user["email"],
                    "mobile_no": target_user.get("mobile_no")
                },
                "assignments": assignments_data,
                "total_count": len(assignments_data)
            }
        )
    
    except Exception as e:
        import traceback
        log.error(f"Failed to get user assignments: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to get user assignments: {str(e)}"
        )



async def remove_role_from_user(
    request: Request,
    assignment_id: str,
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )
        
        token = authorization.split(" ")[1]
        token_payload = decode_access_token(token)
        current_user_id = token_payload.get("sub")
        
        if not current_user_id:
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid token"
            )
        
        try:
            assignment_uuid = uuid.UUID(assignment_id)
        except (ValueError, AttributeError):
            return HttpStatusCode.BAD_REQUEST.response(
                message="Invalid assignment_id format"
            )
        
        assignments = await FRTUUserAssignment.select(
            id=assignment_uuid,
            columns=[
                FRTUUserAssignment.id,
                FRTUUserAssignment.user_id,
                FRTUUserAssignment.role_id,
                FRTUUserAssignment.scope_type,
                FRTUUserAssignment.scope_id
            ]
        )
        
        if not assignments:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Assignment with ID '{assignment_id}' not found"
            )
        
        assignment = assignments[0]
        
        user = await FRTUUsers.select(
            id=assignment["user_id"],
            columns=[FRTUUsers.name]
        )
        role = await FRTURoles.select(
            id=assignment["role_id"],
            columns=[FRTURoles.name]
        )
        
        user_name = user[0]["name"] if user else "Unknown"
        role_name = role[0]["name"] if role else "Unknown"
        
        await FRTUUserAssignment.delete(
            conditions={"id": assignment_uuid}
        )
        
        return HttpStatusCode.OK.response(
            message=f"Role '{role_name}' removed from user '{user_name}' successfully",
            data={
                "assignment_id": assignment_id,
                "user_name": user_name,
                "role_name": role_name,
                "scope_type": assignment["scope_type"]
            }
        )
    
    except Exception as e:
        import traceback
        log.error(f"Failed to remove role from user: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to remove role: {str(e)}"
        )


async def get_all_user_assignments(
    request: Request,
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )
        
        token = authorization.split(" ")[1]
        token_payload = decode_access_token(token)
        
        role_name_filter = request.query_params.get("role_name")
        scope_type_filter = request.query_params.get("scope_type")
        
        filters = {}
        if scope_type_filter:
            filters["scope_type"] = scope_type_filter
        
        assignments = await FRTUUserAssignment.select(
            columns=[
                FRTUUserAssignment.id,
                FRTUUserAssignment.user_id,
                FRTUUserAssignment.role_id,
                FRTUUserAssignment.scope_type,
                FRTUUserAssignment.scope_id,
                FRTUUserAssignment.creation_time
            ],
            **filters
        )
        
        if not assignments:
            return HttpStatusCode.OK.response(
                message="No user assignments found",
                data={
                    "assignments": [],
                    "total_count": 0
                }
            )
        
        if role_name_filter:
            roles = await FRTURoles.select(
                name=role_name_filter,
                columns=[FRTURoles.id]
            )
            if roles:
                role_id = roles[0]["id"]
                assignments = [a for a in assignments if a["role_id"] == role_id]
        
        assignments_data = []
        
        for assignment in assignments:
            users = await FRTUUsers.select(
                id=assignment["user_id"],
                columns=[FRTUUsers.id, FRTUUsers.name, FRTUUsers.email]
            )
            
            roles = await FRTURoles.select(
                id=assignment["role_id"],
                columns=[FRTURoles.id, FRTURoles.name, FRTURoles.description]
            )
            
            if users and roles:
                user = users[0]
                role = roles[0]
                
                assignments_data.append({
                    "assignment_id": str(assignment["id"]),
                    "user": {
                        "id": str(user["id"]),
                        "name": user["name"],
                        "email": user["email"]
                    },
                    "role": {
                        "id": str(role["id"]),
                        "name": role["name"],
                        "description": role.get("description")
                    },
                    "scope": {
                        "type": assignment["scope_type"],
                        "id": str(assignment["scope_id"])
                    },
                    "assigned_at": assignment["creation_time"].isoformat() if assignment.get("creation_time") else None
                })
        
        return HttpStatusCode.OK.response(
            message="All user assignments retrieved successfully",
            data={
                "assignments": assignments_data,
                "total_count": len(assignments_data)
            }
        )
    
    except Exception as e:
        import traceback
        log.error(f"Failed to get all user assignments: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to get user assignments: {str(e)}"
        )


async def update_user_assignment_scope(
    request: Request,
    assignment_id: str,
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )
        
        token = authorization.split(" ")[1]
        token_payload = decode_access_token(token)
        
        try:
            assignment_uuid = uuid.UUID(assignment_id)
        except (ValueError, AttributeError):
            return HttpStatusCode.BAD_REQUEST.response(
                message="Invalid assignment_id format"
            )
        
        assignments = await FRTUUserAssignment.select(
            id=assignment_uuid,
            columns=[
                FRTUUserAssignment.id,
                FRTUUserAssignment.user_id,
                FRTUUserAssignment.role_id
            ]
        )
        
        if not assignments:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Assignment with ID '{assignment_id}' not found"
            )
        
        assignment = assignments[0]
        
        payload = await request.json()
        new_scope_type = payload.get("scope_type")
        new_scope_id_str = payload.get("scope_id")
        
        if not new_scope_type or not new_scope_id_str:
            return HttpStatusCode.BAD_REQUEST.response(
                message="'scope_type' and 'scope_id' are required"
            )
        
        try:
            new_scope_id = uuid.UUID(new_scope_id_str)
        except (ValueError, AttributeError):
            return HttpStatusCode.BAD_REQUEST.response(
                message="Invalid scope_id format"
            )
        
        valid_scope_types = ["TENANT", "PROJECT", "SITE", "DEVICE", "SLOT", "MODULE"]
        if new_scope_type not in valid_scope_types:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"Invalid scope_type. Must be one of: {', '.join(valid_scope_types)}"
            )
        
        now = datetime.utcnow()
        await FRTUUserAssignment.update(
            extra={},
            conditions={"id": assignment_uuid},
            scope_type=new_scope_type,
            scope_id=new_scope_id,
            last_update_time=now
        )
        
        return HttpStatusCode.OK.response(
            message="Assignment scope updated successfully",
            data={
                "assignment_id": assignment_id,
                "new_scope": {
                    "type": new_scope_type,
                    "id": str(new_scope_id)
                }
            }
        )
    
    except Exception as e:
        import traceback
        log.error(f"Failed to update assignment scope: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to update assignment: {str(e)}"
        )