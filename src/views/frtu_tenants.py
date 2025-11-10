import secrets
import uuid
from click import UUID
from fastapi import HTTPException, Header, Request, Depends, status
from fastapi.responses import JSONResponse
from src import Settings, HttpStatusCode
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_roles import FRTURoles
from src.models.frtu_tenants import FRTUTenants
from src.models.frtu_users import FRTUUsers
from src.schemas.frtu_tenants import FRTUTenantCreate, FRTUTenantRead
from datetime import datetime, UTC, timedelta
from src.utils.jwt_tokens import create_access_token, decode_access_token
from src.utils.schema import verify_schema
import jwt
from src.config.auth_config import SECRET_KEY, ALGORITHM
from src.utils.security import hash_password



# create tenant under specific admin
# async def create_tenant(request: Request, settings: Settings):
#     try:
#         admin_name = request.query_params.get("admin_name")
#         if not admin_name:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="Missing admin_name in query params"
#             )

#         payload = await request.json()
#         name = payload.get("name")
#         if not name:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message="Tenant 'name' is required in payload"
#             )

#         admin = await FRTUPlatformAdmin.select(name=admin_name)
#         if not admin:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"Admin '{admin_name}' not found"
#             )

#         admin_id = admin[0]["id"]

#         existing = await FRTUTenants.select(admin_id=admin_id, name=name)
#         if existing:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message=f"Tenant '{name}' already exists for admin '{admin_name}'"
#             )

#         attributes = {k: v for k, v in payload.items() if k != "name"}

#         now = datetime.now(UTC).replace(tzinfo=None)

#         value = await FRTUTenants.insert(
#             admin_id=admin_id,
#             name=name,
#             attribute=attributes,
#             creation_time=now,
#             last_update_time=now
#         )

#         response_data = {
#             "id": str(value.id),
#             "admin_id": str(value.admin_id),
#             "name": value.name,
#             "attribute": value.attribute,
#             "creation_time": value.creation_time.isoformat() if value.creation_time else None,
#             "last_update_time": value.last_update_time.isoformat() if value.last_update_time else None,
#         }

#         return HttpStatusCode.CREATED.response(
#             message="Tenant created successfully",
#             data=response_data
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# get list of all tenant under specific admin
async def get_tenants(request: Request):
    try:
        admin_name = request.query_params.get("admin_name")
        if not admin_name:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Missing admin_name in query params"
            )

        admin = await FRTUPlatformAdmin.select(name=admin_name)
        if not admin:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Admin '{admin_name}' not found"
            )

        admin_id = admin[0]["id"]

        tenants = await FRTUTenants.select(admin_id=admin_id)
        if not tenants:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"No tenants found for admin '{admin_name}'"
            )

        response_data = []
        for tenant in tenants:
            tenant_dict = dict(tenant)
            if tenant_dict.get("creation_time"):
                tenant_dict["creation_time"] = tenant_dict["creation_time"].isoformat()
            if tenant_dict.get("last_update_time"):
                tenant_dict["last_update_time"] = tenant_dict["last_update_time"].isoformat()

            if tenant_dict.get("id"):
                tenant_dict["id"] = str(tenant_dict["id"])
            if tenant_dict.get("admin_id"):
                tenant_dict["admin_id"] = str(tenant_dict["admin_id"])

            response_data.append(tenant_dict)

        return HttpStatusCode.OK.response(
            message=f"{len(response_data)} tenant(s) fetched for admin '{admin_name}'",
            data=response_data
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# get specific tenant( by tenant name ) under specific admin
async def get_tenant_by_name(request: Request):
    try:
        admin_name = request.query_params.get("admin_name")
        tenant_name = request.query_params.get("tenant_name")

        if not admin_name or not tenant_name:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Missing required query params: admin_name and tenant_name"
            )

        admin = await FRTUPlatformAdmin.select(name=admin_name)
        if not admin:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Admin '{admin_name}' not found"
            )

        admin_id = admin[0]["id"]

        tenants = await FRTUTenants.select(admin_id=admin_id, name=tenant_name)
        if not tenants:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Tenant '{tenant_name}' not found for admin '{admin_name}'"
            )

        tenant = dict(tenants[0])

        if tenant.get("id"):
            tenant["id"] = str(tenant["id"])
        if tenant.get("admin_id"):
            tenant["admin_id"] = str(tenant["admin_id"])
        if tenant.get("creation_time"):
            tenant["creation_time"] = tenant["creation_time"].isoformat()
        if tenant.get("last_update_time"):
            tenant["last_update_time"] = tenant["last_update_time"].isoformat()

        return HttpStatusCode.OK.response(
            message=f"Tenant '{tenant_name}' fetched for admin '{admin_name}'",
            data=tenant
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# update tenant detail for specific admin
async def update_tenant(request: Request):
    try:
        tenant_name = request.query_params.get("tenant_name")
        admin_name = request.query_params.get("admin_name")

        if not tenant_name or not admin_name:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Missing 'tenant_name' or 'admin_name' in query params"
            )

        admin = await FRTUPlatformAdmin.select(name=admin_name)
        if not admin:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Admin '{admin_name}' not found"
            )
        admin_id = admin[0]["id"]

        tenants = await FRTUTenants.select(admin_id=admin_id, name=tenant_name)
        if not tenants:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Tenant '{tenant_name}' not found for admin '{admin_name}'"
            )
        tenant_id = tenants[0]["id"]

        payload = await request.json()
        updated_attributes = payload or tenants[0]["attribute"] or {}
        # now = datetime.now(UTC)
        now = datetime.utcnow()

        await FRTUTenants.update(
            conditions={"id": tenant_id},
            attribute=updated_attributes,
            last_update_time=now
        )

        updated_tenant = await FRTUTenants.select(admin_id=admin_id, name=tenant_name)
        tenant_dict = dict(updated_tenant[0])
        tenant_dict["id"] = str(tenant_dict["id"])
        tenant_dict["admin_id"] = str(tenant_dict["admin_id"])
        tenant_dict["creation_time"] = tenant_dict["creation_time"].isoformat()
        tenant_dict["last_update_time"] = tenant_dict["last_update_time"].isoformat()

        return HttpStatusCode.OK.response(
            message=f"Tenant '{tenant_name}' updated successfully",
            data=tenant_dict
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# delete tenant of specific admin
async def delete_tenant(request: Request):
    try:
        tenant_name = request.query_params.get("tenant_name")
        admin_name = request.query_params.get("admin_name")

        if not tenant_name or not admin_name:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Missing 'tenant_name' or 'admin_name' in query params"
            )

        admin = await FRTUPlatformAdmin.select(name=admin_name)
        if not admin:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Admin '{admin_name}' not found"
            )
        admin_id = admin[0]["id"]

        tenants = await FRTUTenants.select(admin_id=admin_id, name=tenant_name)
        if not tenants:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Tenant '{tenant_name}' not found for admin '{admin_name}'"
            )
        tenant_id = tenants[0]["id"]

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if projects:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"Tenant '{tenant_name}' cannot be deleted because it has projects"
            )

        await FRTUTenants.delete(conditions={"id": tenant_id})

        return HttpStatusCode.OK.response(
            message=f"Tenant '{tenant_name}' deleted successfully"
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# tenant_auth.py
def create_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def create_tenant(request: Request,authorization: str = Header(...)):
    try:
        if not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response("Invalid Authorization header")

        token = authorization.split(" ")[1]
        token_data = decode_access_token(token)
        platform_admin_user_id = token_data.get("sub")
        if not platform_admin_user_id:
            return HttpStatusCode.UNAUTHORIZED.response("Invalid token: user_id missing")

        platform_admin_user_id = uuid.UUID(platform_admin_user_id)

        admin_profile = await FRTUPlatformAdmin.select(id=platform_admin_user_id)
        # super_admin_profile = await FRTUUsers.select(id=platform_admin_user_id)
        if not admin_profile:
            return HttpStatusCode.BAD_REQUEST.response("Only Platform Admin can create tenants")

        admin_id = admin_profile[0]["id"]  

        payload = await request.json()
        name = payload.get("name")
        attribute = payload.get("attribute") or {}

        if not name:
            return HttpStatusCode.BAD_REQUEST.response("Tenant 'name' is required")

        existing = await FRTUTenants.select(admin_id=admin_id, name=name)
        if existing:
            return HttpStatusCode.BAD_REQUEST.response(f"Tenant '{name}' already exists")

        now = datetime.utcnow()

        tenant = await FRTUTenants.insert(
            admin_id=admin_id,
            name=name,
            attribute=attribute,
            creation_time=now,
            last_update_time=now
        )

        return HttpStatusCode.CREATED.response(
            message="Tenant created successfully",
            data={
                "tenant_id": str(tenant.id),
                "name": name,
                "admin_id": str(admin_id),
                "attribute": attribute
            }
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(str(e))


# async def create_tenant(request: Request, authorization: str = Header(...)):
#     try:
#         if not authorization or not authorization.startswith("Bearer "):
#             return HttpStatusCode.UNAUTHORIZED.response("Invalid Authorization header")

#         token = authorization.split(" ")[1]
#         token_data = decode_access_token(token)

#         user_id = token_data.get("sub")
#         if not user_id:
#             return HttpStatusCode.UNAUTHORIZED.response("Invalid token: user_id missing")

#         user_uuid = uuid.UUID(user_id)

#         user_roles = await FRTURoles.select(user_id=user_uuid)
#         if not user_roles:
#             return HttpStatusCode.UNAUTHORIZED.response("User has no assigned role")

#         role_names = [r["name"].strip().lower() for r in user_roles]

#         if not any(role in ["super admin", "platform admin"] for role in role_names):
#             return HttpStatusCode.BAD_REQUEST.response("Only Super Admin or Platform Admin can create tenants")

#         admin_profile = []
#         if "platform admin" in role_names:
#             admin_profile = await FRTUPlatformAdmin.select(id=user_uuid)
#         elif "super admin" in role_names:
#             admin_profile = await FRTUUsers.select(id=user_uuid)

#         if not admin_profile:
#             return HttpStatusCode.UNAUTHORIZED.response("Admin profile not found")

#         payload = await request.json()
#         name = payload.get("name")
#         attribute = payload.get("attribute") or {}

#         if not name:
#             return HttpStatusCode.BAD_REQUEST.response("Tenant 'name' is required")

#         existing = await FRTUTenants.select(name=name)
#         if existing:
#             return HttpStatusCode.BAD_REQUEST.response(f"Tenant '{name}' already exists")

#         now = datetime.utcnow()

#         tenant = await FRTUTenants.insert(
#             admin_id=user_uuid,
#             name=name,
#             attribute=attribute,
#             creation_time=now,
#             last_update_time=now
#         )

#         return HttpStatusCode.CREATED.response(
#             message="Tenant created successfully",
#             data={
#                 "tenant_id": str(tenant.id),
#                 "name": name,
#                 "created_by_roles": role_names,
#                 "admin_id": str(user_uuid),
#                 "attribute": attribute
#             }
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(str(e))



async def create_tenant_user(request: Request,authorization: str = Header(...)):
    try:
        if not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response("Invalid Authorization header")

        token = authorization.split(" ")[1]
        token_data = decode_access_token(token)

        # Allow only platform admin
        # if token_data.get("role") != "platform_admin":
        #     return HttpStatusCode.BAD_REQUEST.response("Only Platform Admin can create tenant users")

        payload = await request.json()

        tenant_id_str = payload.get("tenant_id")
        name = payload.get("name")
        email = payload.get("email")
        mobile_no = payload.get("mobile_no")
        attribute = payload.get("attribute") or {}
        password = payload.get("password")

        if not tenant_id_str:
            return HttpStatusCode.BAD_REQUEST.response("tenant_id is required")

        tenant_id = uuid.UUID(tenant_id_str)

        tenant = await FRTUTenants.select(id=tenant_id)
        if not tenant:
            return HttpStatusCode.NOT_FOUND.response("Tenant not found")

        if not name:
            return HttpStatusCode.BAD_REQUEST.response("User name is required")

        if not email and not mobile_no:
            return HttpStatusCode.BAD_REQUEST.response("Email or mobile_no required")

        filters = {}
        if email:
            filters["email"] = email
        if mobile_no:
            filters["mobile_no"] = mobile_no

        existing = await FRTUUsers.select(**filters)
        if existing:
            return HttpStatusCode.BAD_REQUEST.response("User already exists")

        salt = uuid.uuid4().hex
        password_hash = hash_password(password, salt)

        attribute["tenant_id"] = tenant_id_str

        now = datetime.utcnow()

        user_obj = await FRTUUsers.insert(
            name=name,
            email=email or "",
            mobile_no=mobile_no or "",
            password_hash=password_hash,
            salt=salt,
            attribute=attribute,
            creation_time=now,
            last_update_time=now
        )

        return HttpStatusCode.CREATED.response(
            message="Tenant User created successfully",
            data={
                "user_id": str(user_obj.id),
                "name": name,
                "email": email,
                "mobile_no": mobile_no,
                "tenant_id": tenant_id_str
            }
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(str(e))


async def tenant_login(request: Request):
    try:
        payload = await request.json()
        identifier = payload.get("email") or payload.get("mobile_no")
        password = payload.get("password")

        if not identifier or not password:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "email or mobile_no and password are required"}
            )
        filters = {"email": identifier} if "@" in identifier else {"mobile_no": identifier}
        filters["user_type"] = "tenant_admin"
        
        users = await FRTUUsers.select(**filters)
        if not users:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Tenant Admin not found"}
            )

        user = users[0]
        if hash_password(password, user["salt"]) != user["password_hash"]:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "Invalid credentials"}
            )

        tenants = await FRTUTenants.select(admin_id=user["id"])
        if not tenants:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "No tenant organization found for this admin"}
            )
        
        tenant = tenants[0]

        token = create_access_token(
            sub=str(user["id"]),
            extra_claims={
                "user_type": "tenant_admin",
                "name": user["name"],
                "tenant_id": str(tenant["id"]),
                "tenant_name": tenant["name"]
            },
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Tenant Admin login successful",
                "data": {
                    "access_token": token,
                    "token_type": "Bearer",
                    "user_id": str(user["id"]),
                    "tenant_id": str(tenant["id"]),
                    "tenant_name": tenant["name"]
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": str(e)}
        )


