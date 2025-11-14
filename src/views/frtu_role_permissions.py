
from fastapi import HTTPException, Request, Header, Depends, status
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_roles import FRTURoles
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_users import FRTUUsers
from src.core.status_codes import HttpStatusCode
from src.schemas.frtu_role_permissions import AssignRolePermission, FRTURolePermissionBase
from src.utils.jwt_tokens import decode_access_token
from src.core.settings import Settings
from src import log
from datetime import UTC, datetime
import uuid
from uuid import UUID


async def assign_permission_to_role(data: AssignRolePermission, assigned_by: UUID):

    role = await FRTURoles.select(id=data.role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    role = role[0]

    role_created_by = role.user_id
    # if isinstance(role.attribute, dict):
    #     role_created_by = role.attribute.get("created_by")

    perm = await FRTUPermissions.select(id=data.permission_id)
    if not perm:
        raise HTTPException(404, "Permission not found")
    perm = perm[0]

    permission_created_by = perm.user_id

    mapping = await FRTURolePermissions.insert(
        role_id=data.role_id,
        permission_id=data.permission_id,
        creation_time=datetime.utcnow(),
        last_update_time=datetime.utcnow(),
    )

    return {
        "role_id": mapping.role_id,
        "permission_id": mapping.permission_id,

        "assigned_by": assigned_by,
        "role_created_by": role_created_by,
        "permission_created_by": permission_created_by,

        "creation_time": mapping.creation_time,
        "last_update_time": mapping.last_update_time,
    }



async def remove_permissions_from_role(
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
        current_user_id = token_payload.get("sub")
        
        if not current_user_id:
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid token"
            )
        payload = await request.json()
        role_name = payload.get("role_name")
        role_id_str = payload.get("role_id")
        permission_ids = payload.get("permission_ids", [])
        
        if not permission_ids or not isinstance(permission_ids, list):
            return HttpStatusCode.BAD_REQUEST.response(
                message="'permission_ids' is required and must be a non-empty array"
            )
        role = None
        if role_name:
            roles = await FRTURoles.select(
                name=role_name,
                columns=[FRTURoles.id, FRTURoles.name, FRTURoles.attribute]
            )
            if not roles:
                return HttpStatusCode.NOT_FOUND.response(
                    message=f"Role with name '{role_name}' not found"
                )
            role = roles[0]
        elif role_id_str:
            try:
                role_id = uuid.UUID(role_id_str)
                roles = await FRTURoles.select(
                    id=role_id,
                    columns=[FRTURoles.id, FRTURoles.name, FRTURoles.attribute]
                )
                if not roles:
                    return HttpStatusCode.NOT_FOUND.response(
                        message=f"Role with ID '{role_id_str}' not found"
                    )
                role = roles[0]
            except (ValueError, AttributeError):
                return HttpStatusCode.BAD_REQUEST.response(
                    message="Invalid role_id format"
                )
        else:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Either 'role_name' or 'role_id' is required"
            )
        
        role_id = role["id"]
        
        is_system_role = role.get("attribute", {}).get("is_system_role", False)
        if is_system_role:
            return HttpStatusCode.FORBIDDEN.response(
                message="Cannot modify permissions of system roles"
            )
        
        removed_count = 0
        not_found_count = 0
        
        for perm_id_str in permission_ids:
            try:
                perm_id = uuid.UUID(perm_id_str)
                
                existing = await FRTURolePermissions.select(
                    role_id=role_id,
                    permission_id=perm_id,
                    columns=[FRTURolePermissions.role_id]
                )
                
                if not existing:
                    not_found_count += 1
                    continue
                
                await FRTURolePermissions.delete(
                    conditions={
                        "role_id": role_id,
                        "permission_id": perm_id
                    }
                )
                removed_count += 1
                
            except (ValueError, AttributeError):
                return HttpStatusCode.BAD_REQUEST.response(
                    message=f"Invalid permission ID format: {perm_id_str}"
                )
        
        return HttpStatusCode.OK.response(
            message=f"Permissions removed from role '{role['name']}'",
            data={
                "role_id": str(role_id),
                "role_name": role["name"],
                "removed_count": removed_count,
                "not_found_count": not_found_count,
                "total_requested": len(permission_ids)
            }
        )
    
    except Exception as e:
        import traceback
        log.error(f"Failed to remove permissions from role: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to remove permissions: {str(e)}"
        )


async def get_role_permissions(
    request: Request,
    role_name: str = None,
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
        
        role_id_str = request.query_params.get("role_id")
        role = None
        
        if role_name:
            roles = await FRTURoles.select(
                name=role_name,
                columns=[FRTURoles.id, FRTURoles.name, FRTURoles.description, FRTURoles.attribute]
            )
            if not roles:
                return HttpStatusCode.NOT_FOUND.response(
                    message=f"Role with name '{role_name}' not found"
                )
            role = roles[0]
        elif role_id_str:
            try:
                role_id = uuid.UUID(role_id_str)
                roles = await FRTURoles.select(
                    id=role_id,
                    columns=[FRTURoles.id, FRTURoles.name, FRTURoles.description, FRTURoles.attribute]
                )
                if not roles:
                    return HttpStatusCode.NOT_FOUND.response(
                        message=f"Role with ID '{role_id_str}' not found"
                    )
                role = roles[0]
            except (ValueError, AttributeError):
                return HttpStatusCode.BAD_REQUEST.response(
                    message="Invalid role_id format"
                )
        else:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Either role_name in path or role_id in query is required"
            )
        
        role_id = role["id"]
        
        role_perms = await FRTURolePermissions.select(
            role_id=role_id,
            columns=[
                FRTURolePermissions.role_id,
                FRTURolePermissions.permission_id,
                FRTURolePermissions.creation_time
            ]
        )
        
        if not role_perms:
            return HttpStatusCode.OK.response(
                message=f"No permissions assigned to role '{role['name']}'",
                data={
                    "role_id": str(role_id),
                    "role_name": role["name"],
                    "permissions": [],
                    "total_count": 0
                }
            )
        
        permissions_data = []
        
        for rp in role_perms:
            perm_id = rp["permission_id"]
            
            perms = await FRTUPermissions.select(
                id=perm_id,
                columns=[
                    FRTUPermissions.id,
                    FRTUPermissions.user_id,
                    FRTUPermissions.attribute
                ]
            )
            
            if perms:
                perm = perms[0]
                
                creator = None
                if perm.get("user_id"):
                    users = await FRTUUsers.select(
                        id=perm["user_id"],
                        columns=[FRTUUsers.id, FRTUUsers.name, FRTUUsers.email]
                    )
                    if users:
                        creator_user = users[0]
                        creator = {
                            "user_id": str(creator_user["id"]),
                            "name": creator_user["name"],
                            "email": creator_user["email"]
                        }
                
                permissions_data.append({
                    "permission_id": str(perm["id"]),
                    "attribute": perm.get("attribute", []),
                    "resources_count": len(perm.get("attribute", [])) if isinstance(perm.get("attribute"), list) else 0,
                    "created_by": creator,
                    "assigned_at": rp["creation_time"].isoformat() if rp.get("creation_time") else None
                })
        
        return HttpStatusCode.OK.response(
            message=f"Permissions for role '{role['name']}' retrieved successfully",
            data={
                "role_id": str(role_id),
                "role_name": role["name"],
                "role_description": role.get("description"),
                "permissions": permissions_data,
                "total_count": len(permissions_data)
            }
        )
    
    except Exception as e:
        import traceback
        log.error(f"Failed to get role permissions: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to get role permissions: {str(e)}"
        )


async def get_all_role_permissions(
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
        
        all_mappings = await FRTURolePermissions.select(
            columns=[
                FRTURolePermissions.role_id,
                FRTURolePermissions.permission_id,
                FRTURolePermissions.creation_time
            ]
        )
        
        if not all_mappings:
            return HttpStatusCode.OK.response(
                message="No role-permission mappings found",
                data={
                    "mappings": [],
                    "total_count": 0
                }
            )
        role_mappings = {}
        
        for mapping in all_mappings:
            role_id = mapping["role_id"]
            
            if role_id not in role_mappings:
                role_mappings[role_id] = {
                    "role_id": str(role_id),
                    "permission_ids": []
                }
            
            role_mappings[role_id]["permission_ids"].append(str(mapping["permission_id"]))
        
        result = []
        
        for role_id, data in role_mappings.items():
            roles = await FRTURoles.select(
                id=role_id,
                columns=[FRTURoles.id, FRTURoles.name, FRTURoles.description]
            )
            
            if roles:
                role = roles[0]
                result.append({
                    "role_id": str(role["id"]),
                    "role_name": role["name"],
                    "role_description": role.get("description"),
                    "permissions_count": len(data["permission_ids"]),
                    "permission_ids": data["permission_ids"]
                })
        
        return HttpStatusCode.OK.response(
            message="All role-permission mappings retrieved successfully",
            data={
                "mappings": result,
                "total_roles": len(result)
            }
        )
    
    except Exception as e:
        import traceback
        log.error(f"Failed to get all role permissions: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to get all role permissions: {str(e)}"
        )

