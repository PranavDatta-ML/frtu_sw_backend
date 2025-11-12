from datetime import UTC, datetime, timedelta, timezone
import uuid
from fastapi import Request, HTTPException
from fastapi.params import Header
from src.models.frtu_entities import FRTUEntities
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.models.frtu_roles import FRTURoles
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_users import FRTUUsers
from src.schemas.auth import AuthBase
from src.schemas.frtu_platform_admins import FRTUPlatformAdminCreate, FRTUPlatformAdminUpdate
from src.models.frtu_devices import FRTUDevices
from src.utils.jwt_tokens import create_access_token, decode_access_token
from src.utils.schema import verify_schema
import jwt
from src import Settings, HttpStatusCode
from src.utils.security import hash_password
from uuid import UUID

async def create(request: Request, settings: Settings):
    try:
        payload = await request.json()
        admin_data = FRTUPlatformAdminCreate(**payload)

        insert_data = admin_data.model_dump()
        insert_data["attribute"] = insert_data.get("attribute") or {}
        now = datetime.now(UTC).replace(tzinfo=None)
        insert_data["creation_time"] = now
        insert_data["last_update_time"] = now

        await FRTUPlatformAdmin.insert(**insert_data)

        return HttpStatusCode.CREATED.response(message="Admin created!")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def get_admin(request: Request):
    admin_name = request.query_params.get("name")

    try:
        if admin_name:
            admins = await FRTUPlatformAdmin.select(name=admin_name)
        else:
            admins = await FRTUPlatformAdmin.select()  

        if not admins:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Admin '{admin_name}' not found" if admin_name else "No admins found",
                data=[]
            )

        response_data = []
        for admin in admins:
            admin_dict = dict(admin) 

            attrs = admin_dict.pop("attribute", {}) or {}
            for k, v in attrs.items():
                admin_dict[k] = v

            if admin_dict.get("creation_time"):
                admin_dict["creation_time"] = admin_dict["creation_time"].isoformat()
            if admin_dict.get("last_update_time"):
                admin_dict["last_update_time"] = admin_dict["last_update_time"].isoformat()

            if admin_dict.get("id"):
                admin_dict["id"] = str(admin_dict["id"])

            response_data.append(admin_dict)

        if admin_name and len(response_data) == 1:
            response_data = response_data[0]

        return HttpStatusCode.OK.response(
            message=f"{len(response_data) if isinstance(response_data, list) else 1} admin(s) fetched",
            data=response_data
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


async def update_admin(request: Request):
    admin_name = request.query_params.get("name")
    
    if not admin_name:
        return HttpStatusCode.BAD_REQUEST.response(message="Admin 'name' query parameter is required")
    
    try:
        payload = await request.json()
        ok, messages, data = await verify_schema(payload, FRTUPlatformAdminUpdate)
        if not ok:
            return HttpStatusCode.BAD_REQUEST.response(message=messages)
        
        admins = await FRTUPlatformAdmin.select(name=admin_name)
        if not admins:
            return HttpStatusCode.NOT_FOUND.response(message=f"Admin '{admin_name}' not found")
        
        admin_obj = admins[0]  
        update_data = data.dict(exclude_unset=True) 
        
        if "attribute" in update_data and update_data["attribute"] is None:
            update_data["attribute"] = {}

        await FRTUPlatformAdmin.update(conditions={"id": admin_obj.id}, **update_data)

        return HttpStatusCode.OK.response(
            message=f"Admin '{admin_name}' updated successfully",
            data={"updated_fields": list(update_data.keys())}
        )
    
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


async def delete_admin(request: Request):
    admin_name = request.query_params.get("name")
    
    if not admin_name:
        return HttpStatusCode.BAD_REQUEST.response(message="Admin 'name' query parameter is required")
    
    try:
        admins = await FRTUPlatformAdmin.select(name=admin_name)
        if not admins:
            return HttpStatusCode.NOT_FOUND.response(message=f"Admin '{admin_name}' not found")
        
        admin_obj = admins[0]  
        await FRTUPlatformAdmin.delete(conditions={"id": admin_obj.id})
        
        return HttpStatusCode.OK.response(
            message=f"Admin '{admin_name}' deleted successfully",
            data={"id": str(admin_obj.id)}
        )
    
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


async def create_platform_admin(request: Request, authorization: str = Header(...)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.NOT_AUTHENTICATED.response(
                message="Invalid Authorization header"
            )

        token = authorization.split(" ")[1]
        payload = decode_access_token(token)

        user_id = payload.get("sub")
        role_id = payload.get("role_id")

        if not user_id:
            return HttpStatusCode.NOT_AUTHENTICATED.response(
                message="Invalid token: user_id missing"
            )

        if not role_id:
            return HttpStatusCode.NOT_AUTHENTICATED.response(
                message="Invalid token: role_id missing"
            )

        role_data = await FRTURoles.select(id=UUID(role_id))
        if not role_data:
            return HttpStatusCode.NOT_AUTHENTICATED.response(
                message="Invalid role: role not found"
            )

        role_name = role_data[0]["name"].lower().strip()
        if role_name not in ["admin", "super admin"]:
            return HttpStatusCode.NOT_AUTHENTICATED.response(
                message="Only users with role 'Admin' or 'Super Admin' can create Platform Admins."
            )

        created_by = UUID(user_id)

        body = await request.json()
        name = body.get("name")
        email = body.get("email")
        mobile_no = body.get("mobile_no")
        attribute = body.get("attribute") or {}

        if not name or (not email and not mobile_no):
            return HttpStatusCode.BAD_REQUEST.response(
                message="Name and either email or mobile_no are required."
            )

        existing = await FRTUPlatformAdmin.select(email=email) if email else []
        if existing:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Platform Admin already exists with this email."
            )

        now = datetime.now(UTC).replace(tzinfo=None)

        platform_admin = await FRTUPlatformAdmin.insert(
            name=name,
            email=email or "",
            mobile_no=mobile_no or "",
            attribute=attribute,
            creation_time=now,
            last_update_time=now,
        )

        entity_data = {
            "entity_id": platform_admin.id,
            "name": name,
            "email_id": email or "",
            "mobile_no": mobile_no or "",
            "attribute": {"entity_type": "platform_admin", **(attribute or {})},
            "created_by": created_by,
            "creation_time": now,
            "last_update_time": now,
        }

        await FRTUEntities.insert(**entity_data)

        return HttpStatusCode.CREATED.response(
            message="Platform Admin created successfully.",
            data={
                "platform_admin_id": str(platform_admin.id),
                "created_by": str(created_by),
                "name": name,
                "email": email,
                "mobile_no": mobile_no,
                "attribute": attribute,
            },
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))
    
    
# async def create_platform_admin(request: Request, authorization: str = Header(...)):
#     try:
#         if not authorization or not authorization.startswith("Bearer "):
#             return HttpStatusCode.NOT_AUTHENTICATED.response(
#                 message="Invalid Authorization header"
#             )

#         token = authorization.split(" ")[1]
#         payload = decode_access_token(token)

#         role = payload.get("role")
#         user_id = payload.get("sub") 

#         if not role or role.strip().lower() != "admin":
#             return HttpStatusCode.NOT_AUTHENTICATED.response(
#                 message="Only users with role 'Admin' can create Platform Admins."
#             )

#         if not user_id:
#             return HttpStatusCode.NOT_AUTHENTICATED.response(
#                 message="Invalid token: user_id missing"
#             )

#         try:
#             created_by = UUID(user_id)
#         except Exception:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="Invalid user_id format in token"
#             )

#         body = await request.json()
#         name = body.get("name")
#         email = body.get("email")
#         mobile_no = body.get("mobile_no")
#         attribute = body.get("attribute") or {}

#         if not name or (not email and not mobile_no):
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="Name and either email or mobile_no are required."
#             )
#         existing = await FRTUPlatformAdmin.select(email=email) if email else []
#         if existing:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="Platform Admin already exists with this email."
#             )

#         now = datetime.now(UTC).replace(tzinfo=None)

#         platform_admin = await FRTUPlatformAdmin.insert(
#             name=name,
#             email=email or "",
#             mobile_no=mobile_no or "",
#             attribute=attribute,
#             creation_time=now,
#             last_update_time=now,
#         )
#         entity_data = {
#             "entity_id": platform_admin.id,
#             "name": name,
#             "email_id": email or "",
#             "mobile_no": mobile_no or "",
#             "attribute": {"entity_type": "platform_admin", **(attribute or {})},
#             "created_by": created_by,   
#             "creation_time": now,
#             "last_update_time": now,
#         }

#         await FRTUEntities.insert(**entity_data)

#         return HttpStatusCode.CREATED.response(
#             message="Platform Admin created successfully.",
#             data={
#                 "platform_admin_id": str(platform_admin.id),
#                 "created_by": str(created_by),
#                 "name": name,
#                 "email": email,
#                 "mobile_no": mobile_no,
#                 "attribute": attribute,
#             },
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))


async def admin_login(request: Request):
    try:
        payload = await request.json()
        identifier = payload.get("email") or payload.get("mobile_no")
        password = payload.get("password")

        if not identifier or not password:
            return HttpStatusCode.BAD_REQUEST.response(
                message="email or mobile_no and password are required"
            )

        filters = {"email": identifier} if "@" in identifier else {"mobile_no": identifier}
        filters["user_type"] = "platform_admin"  # Only platform admins
        
        users = await FRTUUsers.select(**filters)
        if not users:
            return HttpStatusCode.NOT_FOUND.response(
                message="Platform Admin not found"
            )

        user = users[0]
        
        from src.utils.security import hash_password
        if hash_password(password, user["salt"]) != user["password_hash"]:
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid credentials"
            )

        token = create_access_token(
            sub=str(user["id"]),
            extra_claims={
                "user_type": "platform_admin",
                "name": user["name"],
                "email": user["email"],
                "mobile_no": user["mobile_no"],
            },
        )

        return HttpStatusCode.OK.response(
            message="Platform Admin login successful",
            data={
                "access_token": token,
                "token_type": "Bearer",
                "user_id": str(user["id"]),
                "name": user["name"]
            }
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))



