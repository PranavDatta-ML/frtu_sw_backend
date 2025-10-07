import uuid
from click import UUID
from fastapi import Query, Request
from datetime import datetime, timezone
from src.core.settings import Settings
from src.models.frtu_users import FRTUUsers
from src.utils.jwt_tokens import create_access_token
from src.utils.security import generate_salt, hash_password
from src import HttpStatusCode

async def create_user(request: Request, setting: Settings):
    try:
        payload = await request.json()
        email = payload.get("email")
        mobile_no = payload.get("mobile_no")
        name = payload.get("name")
        password = payload.get("password")
        attribute = payload.get("attribute") or {} 

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

        now = datetime.utcnow()  

        user_obj = await FRTUUsers.insert(
            name=name,
            email=email or "",
            mobile_no=mobile_no or "",
            password_hash=password_hash,
            salt=salt,
            attribute=attribute,  
            creation_time=now,
            last_update_time=now,
        )

        user_dict = {
            "id": str(user_obj.id),
            "name": user_obj.name,
            "email": user_obj.email,
            "mobile_no": user_obj.mobile_no,
            "attribute": user_obj.attribute or {},
            "creation_time": user_obj.creation_time.isoformat() if user_obj.creation_time else None,
            "last_update_time": user_obj.last_update_time.isoformat() if user_obj.last_update_time else None
        }

        return HttpStatusCode.CREATED.response(
            message="User created successfully",
            data=user_dict,
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

async def get_users(request: Request):
    """
    Get list of all users
    """
    try:
        users = await FRTUUsers.select(columns=[
            FRTUUsers.id,
            FRTUUsers.name,
            FRTUUsers.email,
            FRTUUsers.mobile_no,
            FRTUUsers.attribute,
            FRTUUsers.creation_time,
            FRTUUsers.last_update_time,
        ])

        user_list = []
        for row in users:
            user_list.append({
                "id": str(row["id"]),
                "name": row["name"],
                "email": row["email"],
                "mobile_no": row["mobile_no"],
                "attribute": row["attribute"] or {},
                "creation_time": row["creation_time"].isoformat() if row["creation_time"] else None,
                "last_update_time": row["last_update_time"].isoformat() if row["last_update_time"] else None
            })

        return HttpStatusCode.OK.response(
            message="Users fetched successfully",
            data=user_list
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# @router.post("/user/login")
async def login_user(request: Request):
    """
    Login user using email or mobile_no and password.
    Returns JWT access token.
    """
    try:
        payload = await request.json()
        identifier = payload.get("email") or payload.get("mobile_no")
        password = payload.get("password")

        if not identifier or not password:
            return HttpStatusCode.BAD_REQUEST.response(
                message="email or mobile_no and password are required"
            )

        # Fetch user
        filters = {}
        if "@" in identifier:
            filters["email"] = identifier
        else:
            filters["mobile_no"] = identifier

        users = await FRTUUsers.select(**filters)
        if not users:
            return HttpStatusCode.BAD_REQUEST.response(message="Invalid credentials")

        user = users[0]

        # Verify password
        password_hash = hash_password(password, user["salt"])
        if password_hash != user["password_hash"]:
            return HttpStatusCode.BAD_REQUEST.response(message="Invalid credentials")

        # Generate JWT token
        token = create_access_token(sub=str(user["id"]))

        return HttpStatusCode.OK.response(
            message="Login successful",
            data={"access_token": token},
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))
