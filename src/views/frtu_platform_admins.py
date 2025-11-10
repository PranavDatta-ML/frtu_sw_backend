from datetime import UTC, datetime, timedelta, timezone
import uuid
from fastapi import Request, HTTPException
from fastapi.params import Header
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.models.frtu_users import FRTUUsers
from src.schemas.auth import AuthBase
from src.schemas.frtu_platform_admins import FRTUPlatformAdminCreate, FRTUPlatformAdminUpdate
from src.models.frtu_devices import FRTUDevices
from src.utils.jwt_tokens import create_access_token, decode_access_token
from src.utils.schema import verify_schema
import jwt
from src import Settings, HttpStatusCode
from src.utils.security import hash_password
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


# async def admin_login(request: Request):
#     payload = await request.json()
#     name = payload.get("name")
#     mobile_no = payload.get("mobile_no")

#     if not name or not mobile_no:
#         raise HTTPException(status_code=400, detail="name and mobile_no required")

#     admin = await FRTUPlatformAdmin.select(name=name, mobile_no=mobile_no)
#     if not admin:
#         raise HTTPException(status_code=404, detail="Admin not found")

#     admin_id = str(admin[0]["id"])
#     token = create_access_token({"admin_id": admin_id, "admin_name": name})
#     return {"token": token, "admin_id": admin_id, "name": name}

# async def admin_login(request: Request):
#     # ok, messages, data = await verify_schema(await request.json(), AuthBase)
#     # if not ok:
#     #     return HttpStatusCode.BAD_REQUEST.response(message=messages)

#     try:
#         payload = await request.json()
#         name = payload.get("name")
#         mobile_no = payload.get("mobile_no")
#         email = payload.get("email")

#         if not name or (not mobile_no and not email):
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="Missing required fields: 'name' and either 'mobile_no' or 'email'."
#             )
#         condition = {"name": name}
#         admins = await FRTUPlatformAdmin.select(**condition)
#         if not admins:
#             return HttpStatusCode.NOT_FOUND.response(message="Admin not found.")

#         admin = admins[0]
#         if mobile_no and admin.get("mobile_no") != mobile_no:
#             return HttpStatusCode.BAD_REQUEST.response(message="Invalid mobile number.")
#         if email and admin.get("email") != email:
#             return HttpStatusCode.BAD_REQUEST.response(message="Invalid email address.")

#         token = create_access_token(
#             sub=str(admin["id"]),
#             extra_claims={
#                 "role": "platform_admin",
#                 "name": admin["name"],
#                 "mobile_no": admin["mobile_no"],
#             },
#         )

#         return HttpStatusCode.OK.response(
#             message="Admin login successful.",
#             data={"access_token": token, "token_type": "Bearer"},
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))


async def create_platform_admin(request: Request,authorization: str = Header(...)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )

        token = authorization.split(" ")[1]
        token_payload = decode_access_token(token)
        
        # if token_payload.get("user_type") != "super_admin":
        #     return HttpStatusCode.BAD_REQUEST.response(
        #         message="Access denied. Only Super Admin can create Platform Admins."
        # )

        payload = await request.json()
        
        name = payload.get("name")
        email = payload.get("email")
        mobile_no = payload.get("mobile_no")
        password = payload.get("password")
        
        if not name or not password or (not email and not mobile_no):
            return HttpStatusCode.BAD_REQUEST.response(
                message="name, password, and either email or mobile_no are required"
            )

        filters = {}
        if email:
            filters["email"] = email
        if mobile_no:
            filters["mobile_no"] = mobile_no

        existing_users = await FRTUUsers.select(**filters)
        if existing_users:
            return HttpStatusCode.BAD_REQUEST.response(
                message="User with this email or mobile_no already exists"
            )

        salt = uuid.uuid4().hex
        password_hash = hash_password(password, salt)
        
        now = datetime.now(UTC).replace(tzinfo=None)
        
        user_obj = await FRTUUsers.insert(
            name=name,
            email=email or "",
            mobile_no=mobile_no or "",
            password_hash=password_hash,
            salt=salt,
            # user_type='platform_admin',  
            attribute=payload.get("attribute") or {},
            creation_time=now,
            last_update_time=now,
        )

        admin_profile = await FRTUPlatformAdmin.insert(
            id=user_obj.id,  # Link to frtu_users
            name=name,
            email=email or "",
            mobile_no=mobile_no or "",
            attribute=payload.get("admin_attribute") or {},
            creation_time=now,
            last_update_time=now
        )

        response_data = {
            "user_id": str(user_obj.id),
            "admin_profile_id": str(admin_profile.id),
            "name": user_obj.name,
            "email": user_obj.email,
            "mobile_no": user_obj.mobile_no,
            # "user_type": "platform_admin",
            "creation_time": user_obj.creation_time.isoformat()
        }

        return HttpStatusCode.CREATED.response(
            message="Platform Admin created successfully!",
            data=response_data
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


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

# async def create_platform_admin(request: Request, authorization: str = Header(...)):
#     try:
#         if not authorization or not authorization.startswith("Bearer "):
#             return HttpStatusCode.UNAUTHORIZED.response(
#                 message="Invalid Authorization header"
#             )

#         token = authorization.split(" ")[1]
#         token_payload = decode_access_token(token)
#         creator_user_id = token_payload.get("sub")

#         if not creator_user_id:
#             return HttpStatusCode.UNAUTHORIZED.response(
#                 message="Invalid token"
#             )

#         creator_user_id = uuid.UUID(creator_user_id)

#         # Check if creator is SUPER ADMIN using roles
#         assignments = await FRTUUserAssignment.select(
#             user_id=creator_user_id,
#             columns=[FRTUUserAssignment.role_id]
#         )

#         if not assignments:
#             return HttpStatusCode.FORBIDDEN.response(
#                 message="Only SUPER ADMIN can create Platform Admins"
#             )

#         role_ids = [a["role_id"] for a in assignments]
#         roles = await FRTURoles.select(id=role_ids)

#         if not any(r["name"] == "SUPER_ADMIN" for r in roles):
#             return HttpStatusCode.FORBIDDEN.response(
#                 message="Only SUPER ADMIN can create Platform Admins"
#             )

#         # ✅ SUPER ADMIN verified

#         payload = await request.json()
        
#         name = payload.get("name")
#         email = payload.get("email")
#         mobile_no = payload.get("mobile_no")
#         password = payload.get("password")

#         if not name or not password or (not email and not mobile_no):
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="name, password, and either email or mobile_no are required"
#             )

#         # Check if user already exists
#         filters = {}
#         if email:
#             filters["email"] = email
#         if mobile_no:
#             filters["mobile_no"] = mobile_no

#         existing_user = await FRTUUsers.select(**filters)
#         if existing_user:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="User with this email or mobile_no already exists"
#             )

#         # Create user account
#         salt = uuid.uuid4().hex
#         password_hash = hash_password(password, salt)
#         now = datetime.utcnow()

#         user_record = await FRTUUsers.insert(
#             name=name,
#             email=email or "",
#             mobile_no=mobile_no or "",
#             password_hash=password_hash,
#             salt=salt,
#             attribute=payload.get("attribute") or {},
#             creation_time=now,
#             last_update_time=now
#         )

#         # Create platform admin profile
#         admin_profile = await FRTUPlatformAdmin.insert(
#             admin_id=user_record.id,
#             name=name,
#             email=email or "",
#             mobile_no=mobile_no or "",
#             attribute=payload.get("attribute", {}).get("admin_attribute") or {},
#             creation_time=now,
#             last_update_time=now
#         )

#         # Optionally auto-assign PLATFORM_ADMIN role
#         role = await FRTURoles.select(name="PLATFORM_ADMIN")
#         if role:
#             await FRTUUserAssignment.insert(
#                 id=uuid.uuid4(),
#                 user_id=user_record.id,
#                 role_id=role[0]["id"],
#                 scope_type="PLATFORM",
#                 scope_id=user_record.id,
#                 attribute={"auto_assigned": True},
#                 creation_time=now,
#                 last_update_time=now
#             )

#         return HttpStatusCode.CREATED.response(
#             message="Platform Admin created successfully",
#             data={
#                 "user_id": str(user_record.id),
#                 "platform_admin_id": str(admin_profile.id),
#                 "name": user_record.name,
#                 "email": user_record.email,
#                 "mobile_no": user_record.mobile_no
#             }
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))

