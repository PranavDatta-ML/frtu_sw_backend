from datetime import UTC, datetime, timezone
from src import log
from uuid import UUID
import uuid
from fastapi import Depends, Header, Request
from src.core.settings import Settings
from src.core.status_codes import HttpStatusCode
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_roles import FRTURoles
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_users import FRTUUsers
from src.utils.jwt_tokens import decode_access_token


# async def create_role(request: Request, authorization: str = Header(...), settings: Settings = Depends(Settings.get_settings)):
#     try:
#         if not authorization or not authorization.startswith("Bearer "):
#             return HttpStatusCode.UNAUTHORIZED.response(message="Invalid Authorization header")

#         token = authorization.split(" ")[1]
#         token_payload = decode_access_token(token)
#         user_id_str = token_payload.get("sub")

#         if not user_id_str:
#             return HttpStatusCode.UNAUTHORIZED.response(message="Invalid token: user_id missing")
        
#         # Convert string to UUID object
#         try:
#             user_id = uuid.UUID(user_id_str)
#         except (ValueError, AttributeError) as e:
#             return HttpStatusCode.BAD_REQUEST.response(message=f"Invalid user_id format: {str(e)}")
        
#         user_exists = await FRTUUsers.select(id=user_id)
#         if not user_exists:
#             return HttpStatusCode.NOT_FOUND.response(message="User not found")

#         payload = await request.json()
#         name = payload.get("name")
#         if not name:
#             return HttpStatusCode.BAD_REQUEST.response(message="Role 'name' is required")

#         existing = await FRTURoles.select(user_id=user_id, name=name)
#         if existing:
#             return HttpStatusCode.BAD_REQUEST.response(message=f"Role '{name}' already exists for this user")

#         now = datetime.now(UTC).replace(tzinfo=None)
#         attributes = {k: v for k, v in payload.items() if k not in ["name", "description"]}

#         value = await FRTURoles.insert(
#             user_id=user_id,  
#             name=name,
#             description=payload.get("description"),
#             attribute=attributes,
#             creation_time=now,
#             last_update_time=now
#         )

#         data = {
#             "id": str(value.id),
#             "user_id": str(value.user_id),
#             "name": value.name,
#             "description": value.description,
#             "attribute": value.attribute,
#             "creation_time": value.creation_time.isoformat() if value.creation_time else None,
#             "last_update_time": value.last_update_time.isoformat() if value.last_update_time else None
#         }

#         return HttpStatusCode.CREATED.response(message="Role created successfully", data=data)

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))
    

async def create_role(request: Request, authorization: str = Header(...), settings: Settings = Depends(Settings.get_settings)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(message="Invalid Authorization header")

        token = authorization.split(" ")[1]
        token_payload = decode_access_token(token)
        user_id_str = token_payload.get("sub")
        if not user_id_str:
            return HttpStatusCode.UNAUTHORIZED.response(message="Invalid token: user_id missing")

        user_id = uuid.UUID(user_id_str)
        users = await FRTUUsers.select(id=user_id)
        if not users:
            return HttpStatusCode.NOT_FOUND.response(message="User not found")

        payload = await request.json()
        name = payload.get("name")
        description = payload.get("description", "")
        permissions_payload = payload.get("permissions", [])

        if not name:
            return HttpStatusCode.BAD_REQUEST.response(message="Role 'name' is required")

        existing_role = await FRTURoles.select(name=name)
        if existing_role:
            return HttpStatusCode.BAD_REQUEST.response(message=f"Role '{name}' already exists")

        now = datetime.now(UTC).replace(tzinfo=None)
        attributes = {k: v for k, v in payload.items() if k not in ["name", "description", "permissions"]}

        new_role = await FRTURoles.insert(
            user_id=user_id,
            name=name,
            description=description,
            attribute=attributes,
            creation_time=now,
            last_update_time=now
        )
        created_mappings = []
        skipped = []
        if permissions_payload:
            for item in permissions_payload:
                resource = item.get("resource")
                actions = item.get("action", [])
                if not resource or not actions:
                    skipped.append({"resource": resource, "reason": "Missing resource or action"})
                    continue

                permissions = await FRTUPermissions.select(columns=['*'])
                for perm in permissions:
                    for attr in perm.get("attribute", []):
                        if attr.get("resource") == resource and any(a in attr.get("action", []) for a in actions):
                            exists = await FRTURolePermissions.select(
                                role_id=new_role.id,
                                permission_id=perm["id"]
                            )
                            if not exists:
                                await FRTURolePermissions.insert(
                                    role_id=new_role.id,
                                    permission_id=perm["id"],
                                    creation_time=now,
                                    last_update_time=now
                                )
                                created_mappings.append(str(perm["id"]))
                            else:
                                skipped.append({"permission_id": str(perm["id"]), "reason": "Already mapped"})

        return HttpStatusCode.CREATED.response(
            message="Role created successfully and permissions mapped",
            data={
                "role_id": str(new_role.id),
                "role_name": new_role.name,
                "created_permission_ids": created_mappings,
                "skipped": skipped,
                "created_by": {
                    "user_id": str(user_id),
                    "email": users[0]["email"]
                }
            }
        )

    except Exception as e:
        import traceback
        log.error(f"Failed to create role and manage permissions: {traceback.format_exc()}")
        return HttpStatusCode.BAD_REQUEST.response(message=f"Failed to create role: {str(e)}")



async def get_all_roles(request: Request):
    try:
        include_permissions = request.query_params.get("include_permissions", "false").lower() == "true"
        
        roles = await FRTURoles.select(
            columns=[
                FRTURoles.id,
                FRTURoles.user_id,
                FRTURoles.name,
                FRTURoles.description,
                FRTURoles.attribute,
                FRTURoles.creation_time,
                FRTURoles.last_update_time
            ]
        )
        
        if not roles:
            return HttpStatusCode.OK.response(message="No roles found",data={"roles": [],"total_count": 0})
        
        roles_data = []
        
        for role in roles:
            creator = None
            if role.get("user_id"):
                users = await FRTUUsers.select(
                    id=role["user_id"],
                    columns=[
                        FRTUUsers.id,
                        FRTUUsers.name,
                        FRTUUsers.email
                    ]
                )
                if users and len(users) > 0:
                    creator_user = users[0]
                    creator = {
                        "user_id": str(creator_user["id"]),
                        "name": creator_user["name"],
                        "email": creator_user["email"]
                    }
            
            permissions_count = 0
            role_perms = []
            role_perms = await FRTURolePermissions.select(
                role_id=role["id"],
                columns=[
                    FRTURolePermissions.role_id,
                    FRTURolePermissions.permission_id
                ]
            )
            if role_perms:
                permissions_count = len(role_perms)

            role_data = {
                "id": str(role["id"]),
                "name": role["name"],
                "description": role.get("description"),
                "attribute": role.get("attribute") if role.get("attribute") is not None else {},
                "permissions_count": permissions_count,
                "is_system_role": role.get("attribute", {}).get("is_system_role", False) if role.get("attribute") else False,
                "created_by": creator,
                "creation_time": role["creation_time"].isoformat() if role.get("creation_time") else None,
                "last_update_time": role["last_update_time"].isoformat() if role.get("last_update_time") else None
            }
            
            if include_permissions and role_perms:
                permissions_list = []
                for rp in role_perms:
                    perm = await FRTUPermissions.select(
                        id=rp["permission_id"],
                        columns=[
                            FRTUPermissions.id,
                            FRTUPermissions.attribute
                        ]
                    )
                    if perm and len(perm) > 0:
                        perm_data = perm[0]
                        permissions_list.append({
                            "permission_id": str(perm_data["id"]),
                            "attribute": perm_data.get("attribute") if perm_data.get("attribute") is not None else []
                        })
                
                role_data["permissions"] = permissions_list
            
            roles_data.append(role_data)
        
        return HttpStatusCode.OK.response(
            message="Roles retrieved successfully",
            data={"roles": roles_data,"total_count": len(roles_data)})
    
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to retrieve roles: {str(e)}"
        )


async def get_role_by_name(request: Request, name: str):
    try:
        roles = await FRTURoles.select(name=name)
        
        if not roles:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Role with name '{name}' not found"
            )
        
        role = roles[0]
        
        creator = None
        if role.get("user_id"):
            users = await FRTUUsers.select(id=role["user_id"])
            if users:
                creator_user = users[0]
                creator = {
                    "user_id": str(creator_user["id"]),
                    "name": creator_user["name"],
                    "email": creator_user["email"]
                }
        
        role_perms = await FRTURolePermissions.select(role_id=role["id"])
        
        permissions_list = []
        if role_perms:
            for rp in role_perms:
                perm = await FRTUPermissions.select(id=rp["permission_id"])
                if perm:
                    perm_data = perm[0]
                    permissions_list.append({
                        "permission_id": str(perm_data["id"]),
                        "attribute": perm_data.get("attribute", [])
                    })
        
        assignments = await FRTUUserAssignment.select(role_id=role["id"])
        assigned_users_count = len(assignments) if assignments else 0
        
        role_data = {
            "id": str(role["id"]),
            "name": role["name"],
            "description": role.get("description"),
            "attribute": role.get("attribute", {}),
            "permissions": permissions_list,
            "permissions_count": len(permissions_list),
            "assigned_users_count": assigned_users_count,
            "is_system_role": role.get("attribute", {}).get("is_system_role", False),
            "created_by": creator,
            "creation_time": role["creation_time"].isoformat() if role.get("creation_time") else None,
            "last_update_time": role["last_update_time"].isoformat() if role.get("last_update_time") else None
        }
        
        return HttpStatusCode.OK.response(
            message="Role retrieved successfully",
            data=role_data
        )
    
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to retrieve role: {str(e)}"
        )
   
    
async def update_role_by_name(request: Request, name: str, authorization: str = Header(...)):
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
        
        roles = await FRTURoles.select(name=name)
        
        if not roles:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Role with name '{name}' not found"
            )
        
        role = roles[0]
        role_id = role["id"]
        
        is_system_role = role.get("attribute", {}).get("is_system_role", False)
        if is_system_role:
            return HttpStatusCode.FORBIDDEN.response(
                message="Cannot modify system roles"
            )
        
        payload = await request.json()
        
        update_fields = {}
        
        if "new_name" in payload:
            new_name = payload["new_name"]
            if new_name != name:
                existing = await FRTURoles.select(name=new_name)
                if existing:
                    return HttpStatusCode.BAD_REQUEST.response(
                        message=f"Role with name '{new_name}' already exists"
                    )
                update_fields["name"] = new_name
        
        if "description" in payload:
            update_fields["description"] = payload["description"]
        
        if "attribute" in payload:
            existing_attr = role.get("attribute", {}) or {}
            new_attr = payload["attribute"]
            merged_attr = {**existing_attr, **new_attr}
            update_fields["attribute"] = merged_attr
        
        if update_fields:
            update_fields["last_update_time"] = datetime.utcnow()
            await FRTURoles.update(
                extra={},
                conditions={"id": role_id},
                **update_fields
            )
        if "permission_ids" in payload:
            permission_ids = payload["permission_ids"]
            
            existing_perms = await FRTURolePermissions.select(role_id=role_id)
            for ep in existing_perms:
                await FRTURolePermissions.delete(
                    conditions={
                        "role_id": role_id,
                        "permission_id": ep["permission_id"]
                    }
                )
            
            now = datetime.utcnow()
            for perm_id_str in permission_ids:
                try:
                    perm_id = uuid.UUID(perm_id_str)
                    perm = await FRTUPermissions.select(id=perm_id)
                    if not perm:
                        return HttpStatusCode.BAD_REQUEST.response(
                            message=f"Permission '{perm_id_str}' not found"
                        )
                    
                    await FRTURolePermissions.insert(
                        role_id=role_id,
                        permission_id=perm_id,
                        creation_time=now,
                        last_update_time=now
                    )
                except (ValueError, AttributeError):
                    return HttpStatusCode.BAD_REQUEST.response(
                        message=f"Invalid permission ID format: {perm_id_str}"
                    )
        
        if "add_permission_ids" in payload:
            add_perm_ids = payload["add_permission_ids"]
            now = datetime.utcnow()
            
            for perm_id_str in add_perm_ids:
                try:
                    perm_id = uuid.UUID(perm_id_str)
                    perm = await FRTUPermissions.select(id=perm_id)
                    if not perm:
                        return HttpStatusCode.BAD_REQUEST.response(
                            message=f"Permission '{perm_id_str}' not found"
                        )
                    
                    existing = await FRTURolePermissions.select(
                        role_id=role_id,
                        permission_id=perm_id
                    )
                    if not existing:
                        await FRTURolePermissions.insert(
                            role_id=role_id,
                            permission_id=perm_id,
                            creation_time=now,
                            last_update_time=now
                        )
                except (ValueError, AttributeError):
                    return HttpStatusCode.BAD_REQUEST.response(
                        message=f"Invalid permission ID format: {perm_id_str}"
                    )
        if "remove_permission_ids" in payload:
            remove_perm_ids = payload["remove_permission_ids"]
            
            for perm_id_str in remove_perm_ids:
                try:
                    perm_id = uuid.UUID(perm_id_str)
                    await FRTURolePermissions.delete(
                        conditions={
                            "role_id": role_id,
                            "permission_id": perm_id
                        }
                    )
                except (ValueError, AttributeError):
                    return HttpStatusCode.BAD_REQUEST.response(
                        message=f"Invalid permission ID format: {perm_id_str}"
                    )
        
        updated_roles = await FRTURoles.select(id=role_id)
        updated_role = updated_roles[0]
        
        updated_perms = await FRTURolePermissions.select(role_id=role_id)
        permissions_count = len(updated_perms) if updated_perms else 0
        
        role_data = {
            "id": str(updated_role["id"]),
            "name": updated_role["name"],
            "description": updated_role.get("description"),
            "attribute": updated_role.get("attribute", {}),
            "permissions_count": permissions_count,
            "creation_time": updated_role["creation_time"].isoformat() if updated_role.get("creation_time") else None,
            "last_update_time": updated_role["last_update_time"].isoformat() if updated_role.get("last_update_time") else None
        }
        
        return HttpStatusCode.OK.response(
            message="Role updated successfully",
            data=role_data
        )
    
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to update role: {str(e)}"
        )


async def delete_role_by_name(request: Request, name: str, authorization: str = Header(...)):
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
        
        roles = await FRTURoles.select(name=name)
        
        if not roles:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Role with name '{name}' not found"
            )
        
        role = roles[0]
        role_id = role["id"]
        
        is_system_role = role.get("attribute", {}).get("is_system_role", False)
        if is_system_role:
            return HttpStatusCode.FORBIDDEN.response(
                message="Cannot delete system roles"
            )
        
        assignments = await FRTUUserAssignment.select(role_id=role_id)
        if assignments:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"Cannot delete role '{name}' as it has {len(assignments)} user(s) assigned. Please remove all assignments first."
            )
        
        role_perms = await FRTURolePermissions.select(role_id=role_id)
        for rp in role_perms:
            await FRTURolePermissions.delete(
                conditions={
                    "role_id": role_id,
                    "permission_id": rp["permission_id"]
                }
            )
        
        await FRTURoles.delete(conditions={"id": role_id})
        
        return HttpStatusCode.OK.response(
            message=f"Role '{name}' deleted successfully",
            data={
                "role_id": str(role_id),
                "role_name": name
            }
        )
    
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to delete role: {str(e)}"
        )


async def get_role_users(request: Request, name: str):
    try:
        roles = await FRTURoles.select(name=name)
        
        if not roles:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Role with name '{name}' not found"
            )
        
        role = roles[0]
        role_id = role["id"]
        
        assignments = await FRTUUserAssignment.select(role_id=role_id)
        
        users_data = []
        
        for assignment in assignments:
            user = await FRTUUsers.select(id=assignment["user_id"])
            if user:
                user_data = user[0]
                users_data.append({
                    "user_id": str(user_data["id"]),
                    "name": user_data["name"],
                    "email": user_data["email"],
                    "mobile_no": user_data.get("mobile_no"),
                    "is_active": user_data.get("is_active", True),
                    "scope_type": assignment.get("scope_type"),
                    "scope_id": str(assignment.get("scope_id")) if assignment.get("scope_id") else None,
                    "assigned_at": assignment["creation_time"].isoformat() if assignment.get("creation_time") else None
                })
        
        return HttpStatusCode.OK.response(
            message=f"Users with role '{name}' retrieved successfully",
            data={
                "role_name": name,
                "users": users_data,
                "total_count": len(users_data)
            }
        )
    
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Failed to retrieve role users: {str(e)}"
        )




