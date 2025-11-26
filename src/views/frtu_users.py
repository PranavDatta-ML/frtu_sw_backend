import uuid
from fastapi import Body, HTTPException, Query, Request, status
from datetime import datetime, timezone
from uuid import UUID
from fastapi.params import Header
from src.core.settings import Settings
from src.models.frtu_entities import FRTUEntities
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_roles import FRTURoles
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_users import FRTUUsers
from src.schemas.auth import AuthBase
from src.schemas.frtu_users import FRTUUserCreate, FRTUUserRead, FRTUUserUpdate
from src.utils.jwt_tokens import create_access_token, decode_access_token
from src.utils.schema import verify_schema
from src.utils.security import generate_salt, hash_password
from src import HttpStatusCode


async def create_user(data: FRTUUserCreate, creator_id: UUID = None):
    # data = payload

    existing = await FRTUUsers.select(email=data.email)
    if existing:
        raise HTTPException(400, "User with this email already exists")

    existing = await FRTUUsers.select(mobile_no=data.mobile_no)
    if existing:
        raise HTTPException(400, "User with this mobile number already exists")

    salt = generate_salt()
    password_hash = hash_password(data.password, salt)

    user = await FRTUUsers.insert(
        name=data.name,
        email=data.email,
        mobile_no=data.mobile_no,
        password_hash=password_hash,
        salt=salt,
        is_active=True,
        is_deleted=False,
        attribute=data.attribute,
        creation_time=datetime.utcnow(),
        last_update_time=datetime.utcnow()
    )

    resp = {
        "created_by": creator_id,
        **user.__dict__
    }

    # await FRTUEntities.insert(
    #     entity_id=user.id,
    #     name=user.name,
    #     email_id=user.email,
    #     mobile_no=user.mobile_no,
    #     created_by=creator_id,
    #     creation_time=datetime.utcnow(),
    #     last_update_time=datetime.utcnow()
    # )

    return resp


async def get_user(user_id: UUID) -> FRTUUserRead:
    user = await FRTUUsers.select(id=user_id)
    if not user:
        raise HTTPException(404, "User not found")

    return FRTUUserRead.from_orm(user[0])


async def update_user(user_id: UUID, data: FRTUUserUpdate) -> FRTUUserRead:
    user_list = await FRTUUsers.select(id=user_id)
    if not user_list:
        raise HTTPException(404, "User not found")

    user = user_list[0]

    if data.name is not None:
        user.name = data.name

    if data.email is not None:
        user.email = data.email

    if data.mobile_no is not None:
        user.mobile_no = data.mobile_no

    if data.attribute is not None:
        user.attribute = data.attribute

    user.last_update_time = datetime.utcnow()
    await user.update()

    return FRTUUserRead.from_orm(user)


async def delete_user(user_id: UUID):
    user_list = await FRTUUsers.select(id=user_id)
    if not user_list:
        raise HTTPException(404, "User not found")

    user = user_list[0]
    await user.delete()

    return {"message": "User deleted successfully"}



# async def get_users(request: Request):
#     try:
#         users = await FRTUUsers.select(columns=[
#             FRTUUsers.id,
#             FRTUUsers.name,
#             FRTUUsers.email,
#             FRTUUsers.mobile_no,
#             FRTUUsers.attribute,
#             FRTUUsers.creation_time,
#             FRTUUsers.last_update_time,
#         ])

#         user_list = []
#         for row in users:
#             user_list.append({
#                 "id": str(row["id"]),
#                 "name": row["name"],
#                 "email": row["email"],
#                 "mobile_no": row["mobile_no"],
#                 "attribute": row["attribute"] or {},
#                 "creation_time": row["creation_time"].isoformat() if row["creation_time"] else None,
#                 "last_update_time": row["last_update_time"].isoformat() if row["last_update_time"] else None
#             })

#         return HttpStatusCode.OK.response(
#             message="Users fetched successfully",
#             data=user_list
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# async def get_user_by_name(request: Request, name: str):
#     try:
#         users = await FRTUUsers.select(name=name, is_deleted=False)
        
#         if not users:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"User with name '{name}' not found"
#             )
        
#         user = users[0]
        
#         user_data = {
#             "id": str(user["id"]),
#             "name": user["name"],
#             "email": user["email"],
#             "mobile_no": user["mobile_no"],
#             "is_active": user.get("is_active", True),
#             "attribute": user.get("attribute", {}),
#             "creation_time": user["creation_time"].isoformat() if user.get("creation_time") else None,
#             "last_update_time": user["last_update_time"].isoformat() if user.get("last_update_time") else None
#         }
        
#         return HttpStatusCode.OK.response(
#             message="User retrieved successfully",
#             data=user_data
#         )
    
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(
#             message=f"Failed to retrieve user: {str(e)}"
#         )

# async def update_user_by_name(request: Request, name: str, authorization: str = Header(...)):
#     try:
#         if not authorization or not authorization.startswith("Bearer "):
#             return HttpStatusCode.UNAUTHORIZED.response(
#                 message="Invalid Authorization header"
#             )
        
#         token = authorization.split(" ")[1]
#         token_payload = decode_access_token(token)
#         current_user_id = token_payload.get("sub")
        
#         if not current_user_id:
#             return HttpStatusCode.UNAUTHORIZED.response(
#                 message="Invalid token"
#             )
        
#         users = await FRTUUsers.select(name=name, is_deleted=False)
        
#         if not users:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"User with name '{name}' not found"
#             )
        
#         user = users[0]
#         user_id = user["id"]
        
#         payload = await request.json()
        
#         update_fields = {}
        
#         if "new_name" in payload:
#             new_name = payload["new_name"]
#             if new_name != name:
#                 existing = await FRTUUsers.select(name=new_name, is_deleted=False)
#                 if existing:
#                     return HttpStatusCode.BAD_REQUEST.response(
#                         message=f"User with name '{new_name}' already exists"
#                     )
#                 update_fields["name"] = new_name
        
#         if "email" in payload:
#             new_email = payload["email"]
#             if new_email != user.get("email"):
#                 existing = await FRTUUsers.select(email=new_email, is_deleted=False)
#                 if existing and existing[0]["id"] != user_id:
#                     return HttpStatusCode.BAD_REQUEST.response(
#                         message=f"Email '{new_email}' is already in use"
#                     )
#                 update_fields["email"] = new_email
        
#         if "mobile_no" in payload:
#             new_mobile = payload["mobile_no"]
#             if new_mobile != user.get("mobile_no"):
#                 existing = await FRTUUsers.select(mobile_no=new_mobile, is_deleted=False)
#                 if existing and existing[0]["id"] != user_id:
#                     return HttpStatusCode.BAD_REQUEST.response(
#                         message=f"Mobile number '{new_mobile}' is already in use"
#                     )
#                 update_fields["mobile_no"] = new_mobile
        
#         if "password" in payload:
#             new_password = payload["password"]
#             if len(new_password) < 6:
#                 return HttpStatusCode.BAD_REQUEST.response(
#                     message="Password must be at least 6 characters"
#                 )
#             new_salt = uuid.uuid4().hex
#             update_fields["salt"] = new_salt
#             update_fields["password_hash"] = hash_password(new_password, new_salt)
        
#         if "is_active" in payload:
#             update_fields["is_active"] = payload["is_active"]
        
#         if "attribute" in payload:
#             # Merge with existing attribute
#             existing_attr = user.get("attribute", {}) or {}
#             new_attr = payload["attribute"]
#             merged_attr = {**existing_attr, **new_attr}
#             update_fields["attribute"] = merged_attr
        
#         if not update_fields:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="No fields to update"
#             )
        
#         update_fields["last_update_time"] = datetime.utcnow()
        
#         await FRTUUsers.update(
#             extra={},
#             conditions={"id": user_id},
#             **update_fields
#         )
        
#         updated_users = await FRTUUsers.select(id=user_id)
#         updated_user = updated_users[0]
        
#         user_data = {
#             "id": str(updated_user["id"]),
#             "name": updated_user["name"],
#             "email": updated_user["email"],
#             "mobile_no": updated_user["mobile_no"],
#             "is_active": updated_user.get("is_active", True),
#             "attribute": updated_user.get("attribute", {}),
#             "creation_time": updated_user["creation_time"].isoformat() if updated_user.get("creation_time") else None,
#             "last_update_time": updated_user["last_update_time"].isoformat() if updated_user.get("last_update_time") else None
#         }
        
#         return HttpStatusCode.OK.response(message="User updated successfully",data=user_data)
    
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=f"Failed to update user: {str(e)}")


# async def delete_user_by_name(request: Request, name: str, authorization: str = Header(...)):
#     try:
#         if not authorization or not authorization.startswith("Bearer "):
#             return HttpStatusCode.UNAUTHORIZED.response(
#                 message="Invalid Authorization header"
#             )
        
#         token = authorization.split(" ")[1]
#         token_payload = decode_access_token(token)
#         current_user_id = token_payload.get("sub")
        
#         if not current_user_id:
#             return HttpStatusCode.UNAUTHORIZED.response(
#                 message="Invalid token"
#             )
        
#         hard_delete = request.query_params.get("hard_delete", "false").lower() == "true"
        
#         users = await FRTUUsers.select(name=name, is_deleted=False)
        
#         if not users:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"User with name '{name}' not found"
#             )
        
#         user = users[0]
#         user_id = user["id"]
        
#         if str(user_id) == current_user_id:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="Cannot delete your own account"
#             )
        
#         if hard_delete:
#             await FRTUUsers.delete(conditions={"id": user_id})
#             message = f"User '{name}' permanently deleted"
#         else:
#             await FRTUUsers.update(
#                 extra={},
#                 conditions={"id": user_id},
#                 is_deleted=True,
#                 is_active=False,
#                 last_update_time=datetime.utcnow()
#             )
#             message = f"User '{name}' deactivated successfully"
        
#         return HttpStatusCode.OK.response(
#             message=message,
#             data={
#                 "user_id": str(user_id),
#                 "name": name,
#                 "deletion_type": "permanent" if hard_delete else "soft"
#             }
#         )
    
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(
#             message=f"Failed to delete user: {str(e)}"
#         )

# async def get_user_with_roles_permissions(request: Request, name: str):
#     try:
        
#         users = await FRTUUsers.select(name=name, is_deleted=False)
        
#         if not users:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"User with name '{name}' not found"
#             )
        
#         user = users[0]
#         user_id = user["id"]
        
#         assignments = await FRTUUserAssignment.select(user_id=user_id)
        
#         roles_data = []
#         all_permissions = set()
        
#         for assignment in assignments:
#             role_id = assignment["role_id"]
            
#             roles = await FRTURoles.select(id=role_id)
#             if roles:
#                 role = roles[0]
                
#                 role_perms = await FRTURolePermissions.select(role_id=role_id)
                
#                 role_permissions = []
#                 for rp in role_perms:
#                     perm = await FRTUPermissions.select(id=rp["permission_id"])
#                     if perm:
#                         perm_data = perm[0]
#                         role_permissions.append({
#                             "permission_id": str(perm_data["id"]),
#                             "attribute": perm_data.get("attribute", [])
#                         })
#                         all_permissions.add(str(perm_data["id"]))
                
#                 roles_data.append({
#                     "role_id": str(role["id"]),
#                     "role_name": role["name"],
#                     "scope_type": assignment.get("scope_type"),
#                     "scope_id": str(assignment.get("scope_id")) if assignment.get("scope_id") else None,
#                     "permissions": role_permissions
#                 })
        
#         user_data = {
#             "id": str(user["id"]),
#             "name": user["name"],
#             "email": user["email"],
#             "mobile_no": user["mobile_no"],
#             "is_active": user.get("is_active", True),
#             "attribute": user.get("attribute", {}),
#             "creation_time": user["creation_time"].isoformat() if user.get("creation_time") else None,
#             "last_update_time": user["last_update_time"].isoformat() if user.get("last_update_time") else None,
#             "roles": roles_data,
#             "total_roles": len(roles_data),
#             "total_unique_permissions": len(all_permissions)
#         }
        
#         return HttpStatusCode.OK.response(message="User details retrieved successfully",data=user_data)
    
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(
#             message=f"Failed to retrieve user details: {str(e)}"
#         )


async def login_user(request: Request):
    try:
        ok, messages, data = await verify_schema(await request.json(), AuthBase)
        if not ok:
            return HttpStatusCode.BAD_REQUEST.response(message=messages)

        username = data.username
        password = data.password

        filters = {"email": username} if "@" in username else {"mobile_no": username}

        users = await FRTUUsers.select(**filters)
        if not users:
            return HttpStatusCode.BAD_REQUEST.response(message="Invalid credentials")

        user = users[0]

        if hash_password(password, user["salt"]) != user["password_hash"]:
            return HttpStatusCode.BAD_REQUEST.response(message="Invalid credentials")

        user_assignment = await FRTUUserAssignment.select(user_id=user["id"])
        role_id = None
        if user_assignment:
            role_id = str(user_assignment[0]["role_id"])
            # role_id = user_assignment[0]["role_id"]
            # role = await FRTURoles.select(id=role_id)
            # if role:
            #     role_name = role[0]["name"]

        # if not role_name:
        #     role_name = "admin" if user["email"].endswith("@etlab.co") else "user"

        token = create_access_token(
            sub=str(user["id"]),
            extra_claims={
                "name": user.get("name"),
                "email": user.get("email"),
                "role_id": role_id
            },
        )

        return HttpStatusCode.OK.response(
            message="Login successful",
            data={
                "access_token": token,
                "user_id": str(user["id"]),
                "role_id": role_id,
                "name": user.get("name"),
                "email": user.get("email")
            },
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

