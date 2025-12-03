from math import ceil
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
from src.schemas.frtu_users import FRTUUserAdd, FRTUUserCreate, FRTUUserRead, FRTUUserUpdate, FRTUUserUpdateById
from src.services.permissions import _user_can_view_all_roles, user_can_assign_roles
from src.services.role import _get_role_permissions, _get_role_permissions_map
from src.utils.jwt_tokens import create_access_token, decode_access_token
from src.utils.schema import verify_schema
from src.utils.security import generate_salt, hash_password
from src import HttpStatusCode
from datetime import UTC
from collections import defaultdict


DEFAULT_PASSWORD = "***REMOVED-DEFAULT-PASSWORD***"

async def create_user(data: FRTUUserAdd, creator_id: UUID | None = None):
    if creator_id is not None:
        allowed = await user_can_assign_roles(creator_id)
        if not allowed:
            return HttpStatusCode.ACCESS_DENIED.response(
                "You are not allowed to create users or assign roles"
            )
    existing_roles = await FRTURoles.select()
    if not existing_roles:
        return {
            "http_code": 400,
            "code": "NO_ROLES_FOUND",
            "message": "No roles exist. Please create a role first."
        }
    if not data.role_id:
        return {
            "http_code": 400,
            "code": "ROLE_REQUIRED",
            "message": "role_id is required to create user"
        }

    role_rows = await FRTURoles.select(id=data.role_id)
    if not role_rows:
        return {
            "http_code": 400,
            "code": "INVALID_ROLE",
            "message": "Role not found for given role_id"
        }
    if not data.mobile_no:
        return {
            "http_code": 400,
            "code": "MOBILE_REQUIRED",
            "message": "Mobile number is required"
        }
    if await FRTUUsers.select(email=data.email):
        return HttpStatusCode.BAD_REQUEST.response("User with this email already exists")

    if await FRTUUsers.select(mobile_no=data.mobile_no):
        return HttpStatusCode.BAD_REQUEST.response("User with this mobile number already exists")

    raw_password = data.password or DEFAULT_PASSWORD
    salt = generate_salt()
    password_hash = hash_password(raw_password, salt)

    now = datetime.now(UTC).replace(tzinfo=None)

    user = await FRTUUsers.insert(
        name=data.name,
        email=data.email,
        mobile_no=data.mobile_no,
        password_hash=password_hash,
        salt=salt,
        is_active=True,
        is_deleted=False,
        attribute=data.attribute or {},
        creation_time=now,
        last_update_time=now,
    )

    await FRTUUserAssignment.insert(
        user_id=user.id,
        role_id=data.role_id,
        scope_type="PLATFORM",
        scope_id=creator_id,
        attribute={},
        admin_id=creator_id,
        creation_time=now,
        last_update_time=now,
    )

    return {
        "http_code": 201,
        "code": "CREATED",
        "message": "User created successfully",
        "data": {
            "created_by": str(creator_id) if creator_id else None,
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "mobile_no": user.mobile_no,
            "last_update_time": user.last_update_time,
            "creation_time": user.creation_time,
            "attribute": user.attribute,
            "role_id": str(data.role_id),
        },
    }


async def read_users(
    page: int,
    limit: int,
    search: str | None,   # can match name or email or mobile
):
    users = await FRTUUsers.select(is_deleted=False)

    if search:
        s = search.lower()
        filtered = []
        for u in users:
            if (
                (u.name and s in u.name.lower())
                or (u.email and s in u.email.lower())
                or (u.mobile_no and s in u.mobile_no.lower())
            ):
                filtered.append(u)
        users = filtered

    total = len(users)
    start = (page - 1) * limit
    end = start + limit
    page_users = users[start:end]

    user_ids = [u.id for u in page_users]
    assignments = await FRTUUserAssignment.select(user_id=user_ids)
    role_ids = {a.role_id for a in assignments}
    roles = await FRTURoles.select(id=list(role_ids)) if role_ids else []
    roles_by_id = {r.id: r for r in roles}

    perms_map = await _get_role_permissions_map(list(role_ids))

    role_by_user: dict[UUID, UUID | None] = {uid: None for uid in user_ids}
    for a in assignments:
        if role_by_user.get(a.user_id) is None:
            role_by_user[a.user_id] = a.role_id

    result = []
    for u in page_users:
        rid = role_by_user.get(u.id)
        role = roles_by_id.get(rid) if rid else None
        perms = perms_map.get(rid, []) if rid else []

        result.append(
            {
                "id": str(u.id),
                "name": u.name,
                "email": u.email,
                "mobile_no": u.mobile_no,
                "is_active": u.is_active,
                "is_deleted": u.is_deleted,
                "attribute": u.attribute or {},
                "creation_time": u.creation_time,
                "last_update_time": u.last_update_time,
                "role": {
                    "id": str(role.id),
                    "name": role.name,
                    "description": role.description,
                } if role else None,
                "permissions": perms,
            }
        )

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Users fetched successfully",
        "page": page,
        "page_size": limit,
        "total_records": total,
        "total_pages": ceil(total / limit) if limit else 1,
        "users": result,
    }

async def read_user_by_id(user_id: UUID):
    users = await FRTUUsers.select(id=user_id, is_deleted=False)
    if not users:
        return HttpStatusCode.NOT_FOUND.response("User not found")
    u = users[0]

    assignments = await FRTUUserAssignment.select(user_id=user_id)
    role_id = assignments[0].role_id if assignments else None

    role = None
    permissions: list[dict] = []
    if role_id:
        roles = await FRTURoles.select(id=role_id)
        role = roles[0] if roles else None
        permissions = await _get_role_permissions(role_id)

    data = {
        "id": str(u.id),
        "name": u.name,
        "email": u.email,
        "mobile_no": u.mobile_no,
        "is_active": u.is_active,
        "is_deleted": u.is_deleted,
        "attribute": u.attribute or {},
        "creation_time": u.creation_time,
        "last_update_time": u.last_update_time,
        "role": {
            "id": str(role.id),
            "name": role.name,
            "description": role.description,
        } if role else None,
        "permissions": permissions,
    }

    return {
        "http_code": 200,
        "code": "OK",
        "message": "User fetched successfully",
        "data": data,
    }

async def update_user_by_id(user_id: UUID, data: FRTUUserUpdateById, updater_id: UUID | None = None):
    if updater_id is not None and updater_id == user_id:
        return HttpStatusCode.ACCESS_DENIED.response(
            "You are not allowed to update your own user details from this endpoint"
        )
    users = await FRTUUsers.select(id=user_id, is_deleted=False)
    if not users:
        return HttpStatusCode.NOT_FOUND.response("User not found")
    u = users[0]

    now = datetime.now(UTC).replace(tzinfo=None)
    updates = {}

    if data.name is not None and data.name != u.name:
        updates["name"] = data.name

    if data.email is not None and data.email != u.email:
        existing = await FRTUUsers.select(email=data.email)
        if existing and existing[0].id != user_id:
            return HttpStatusCode.BAD_REQUEST.response("User with this email already exists")
        updates["email"] = data.email

    if data.mobile_no is not None and data.mobile_no != u.mobile_no:
        existing = await FRTUUsers.select(mobile_no=data.mobile_no)
        if existing and existing[0].id != user_id:
            return HttpStatusCode.BAD_REQUEST.response("User with this mobile number already exists")
        updates["mobile_no"] = data.mobile_no

    if data.attribute is not None:
        merged_attr = {**(u.attribute or {}), **data.attribute}
        updates["attribute"] = merged_attr

    if data.is_active is not None:
        updates["is_active"] = data.is_active

    if updates:
        updates["last_update_time"] = now
        await FRTUUsers.update(conditions={"id": user_id}, **updates)

    if data.role_id is not None:
        roles = await FRTURoles.select(id=data.role_id)
        if not roles:
            return HttpStatusCode.BAD_REQUEST.response("Role not found for given role_id")

        assignments = await FRTUUserAssignment.select(user_id=user_id)
        if assignments:
            ua = assignments[0]
            await FRTUUserAssignment.update(
                conditions={"id": ua.id},
                role_id=data.role_id,
                last_update_time=now,
            )
        else:
            await FRTUUserAssignment.insert(
                user_id=user_id,
                role_id=data.role_id,
                scope_type="PLATFORM",
                scope_id=updater_id,
                attribute={},
                admin_id=updater_id,
                creation_time=now,
                last_update_time=now,
            )

    updated_users = await FRTUUsers.select(id=user_id)
    u2 = updated_users[0]

    read_obj = FRTUUserRead(
        id=u2.id,
        name=u2.name,
        email=u2.email,
        mobile_no=u2.mobile_no,
        is_active=u2.is_active,
        is_deleted=u2.is_deleted,
        attribute=u2.attribute or {},
        creation_time=u2.creation_time,
        last_update_time=u2.last_update_time,
        created_by=updater_id,  # fill if you store creator_id on user
    )

    resp = read_obj.dict()
    if data.role_id is not None:
        resp["role_id"] = str(data.role_id)

    return {
        "http_code": 200,
        "code": "OK",
        "message": "User updated successfully",
        "data": resp,
    }

async def delete_user(user_id: UUID, deleter_id: UUID | None = None, is_deleted: bool = False):
    if not is_deleted:
        return HttpStatusCode.BAD_REQUEST.response(
            "Please confirm delete by passing is_deleted=true"
        )

    if deleter_id is not None and deleter_id == user_id:
        return HttpStatusCode.ACCESS_DENIED.response(
            "You are not allowed to delete your own account"
        )

    users = await FRTUUsers.select(id=user_id)
    if not users:
        return HttpStatusCode.NOT_FOUND.response("User not found")

    u = users[0]
    if u.is_deleted:
        return HttpStatusCode.BAD_REQUEST.response("User is already deleted")

    now = datetime.now(UTC).replace(tzinfo=None)

    await FRTUUsers.update(
        conditions={"id": user_id},
        is_deleted=True,
        is_active=False,
        last_update_time=now,
    )

    await FRTUUserAssignment.delete(conditions={"user_id": user_id})

    return {
        "http_code": 200,
        "code": "OK",
        "message": "User deleted successfully",
        "data": {"id": str(user_id)},
    }

async def read_user_permissions(user_id: UUID):
    # roles assigned to user
    assignments = await FRTUUserAssignment.select(user_id=user_id)
    role_ids = [a.role_id for a in assignments]
    if not role_ids:
        return {
            "http_code": 200,
            "code": "OK",
            "message": "No roles assigned to user",
            "data": {"user_id": str(user_id), "permissions": []},
        }

    rps = await FRTURolePermissions.select(role_id=role_ids)
    perm_ids = [rp.permission_id for rp in rps]
    if not perm_ids:
        return {
            "http_code": 200,
            "code": "OK",
            "message": "No permissions mapped to user roles",
            "data": {"user_id": str(user_id), "permissions": []},
        }

    perms = await FRTUPermissions.select(id=perm_ids)
    perms_by_id = {p.id: (p.attribute or {}) for p in perms}

    merged: dict[str, set[str]] = defaultdict(set)
    for rp in rps:
        attr = perms_by_id.get(rp.permission_id) or {}
        resources_list = attr.get("resources") or []
        for item in resources_list:
            res = item.get("resource")
            actions = item.get("action") or []
            if not res or not actions:
                continue
            for act in actions:
                merged[res].add(act)

    permissions_out = [
        {"resource": res, "actions": sorted(list(acts))}
        for res, acts in merged.items()
    ]

    return {
        "http_code": 200,
        "code": "OK",
        "message": "User permissions fetched successfully",
        "data": {"user_id": str(user_id), "permissions": permissions_out},
    }

async def add_user_api(data: FRTUUserCreate, creator_id: UUID | None = None):
    if not data.role_id:
        raise HTTPException(status_code=400, detail="Role is required. Please create a role first.")

    role_rows = await FRTURoles.select(id=data.role_id)
    if not role_rows:
        raise HTTPException(status_code=400, detail="Invalid role_id. Role not found.")

    existing = await FRTUUsers.select(email=data.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    existing = await FRTUUsers.select(mobile_no=data.mobile_no)
    if existing:
        raise HTTPException(status_code=400, detail="User with this mobile number already exists")

    raw_password = data.password or DEFAULT_PASSWORD
    salt = generate_salt()
    password_hash = hash_password(raw_password, salt)

    now = datetime.now(UTC).replace(tzinfo=None)

    user = await FRTUUsers.insert(
        name=data.name,
        email=data.email,
        mobile_no=data.mobile_no,
        password_hash=password_hash,
        salt=salt,
        is_active=True,
        is_deleted=False,
        attribute=data.attribute or {},
        creation_time=now,
        last_update_time=now,
    )

    # ---------- assign role (mandatory) ----------
    await FRTUUserAssignment.insert(
        user_id=user.id,
        role_id=data.role_id,
        scope_type="PLATFORM",
        scope_id=None,
        attribute={},
        creation_time=now,
        last_update_time=now,
        admin_id=creator_id,
    )

    resp = {
        "created_by": str(creator_id) if creator_id else None,
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "mobile_no": user.mobile_no,
        "role_id": str(data.role_id),
    }

    return resp


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

