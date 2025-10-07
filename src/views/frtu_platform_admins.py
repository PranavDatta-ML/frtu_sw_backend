from datetime import UTC, datetime, timedelta, timezone
from fastapi import Request, HTTPException
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.schemas.frtu_platform_admins import FRTUPlatformAdminCreate, FRTUPlatformAdminUpdate
from src.models.frtu_devices import FRTUDevices
from src.utils.schema import verify_schema
import jwt
from src import Settings, HttpStatusCode
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

# admin_auth.py
from src.config.auth_config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

def create_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def admin_login(request: Request):
    payload = await request.json()
    name = payload.get("name")
    mobile_no = payload.get("mobile_no")

    if not name or not mobile_no:
        raise HTTPException(status_code=400, detail="name and mobile_no required")

    admin = await FRTUPlatformAdmin.select(name=name, mobile_no=mobile_no)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    admin_id = str(admin[0]["id"])
    token = create_token({"admin_id": admin_id, "admin_name": name})
    return {"token": token, "admin_id": admin_id, "name": name}
