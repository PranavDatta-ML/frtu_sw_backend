import uuid
from fastapi import APIRouter, HTTPException, Request, Header, Depends
from src.core.settings import Settings
from src import Settings, HttpStatusCode
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_sites import FRTUSites
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_slots import FRTUSlots
from src.config.auth_config import ALGORITHM, SECRET_KEY
import jwt

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

async def read_slots(
    request: Request,
    authorization: str = Header(..., convert_underscores=False),
    settings: Settings = Depends(Settings.get_settings),
):
    if not authorization or not authorization.startswith("Bearer "):
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid Authorization header"}

    tenant_token = authorization.split(" ")[1]
    try:
        tenant_data = decode_token(tenant_token)
    except Exception as e:
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": f"Tenant token decode failed: {str(e)}"}

    tenant_id_str = tenant_data.get("tenant_id")
    if not tenant_id_str:
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid tenant token: tenant_id missing"}

    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=f"Invalid tenant_id in token: {str(e)}")

    payload = await request.json()
    entity = payload.get("entity", {})
    slot_name = entity.get("name")          
    device_name = entity.get("deviceName") 

    if payload.get("operation") != "read" or payload.get("target") != "slot":
        return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")

    try:
        tenant_projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not tenant_projects:
            return {"http_code": 404, "code": "NOT_FOUND", "message": "No projects found for this tenant"}

        project_ids = [p.id for p in tenant_projects]

        site_filters = {"project_id": project_ids}
        sites = await FRTUSites.select(**site_filters)
        if not sites:
            return {"http_code": 404, "code": "NOT_FOUND", "message": "No sites found for these projects"}

        response_slots = []

        for site in sites:
            site_dict = dict(site)
            site_id = site_dict.get("id")
            site_name = site_dict.get("name")

            device_filters = {"site_id": site_id}
            if device_name:
                device_filters["name"] = device_name

            devices = await FRTUDevices.select(**device_filters)

            for device in devices:
                dev_dict = dict(device)
                dev_id = dev_dict.get("id")
                dev_name = dev_dict.get("name")

                slot_filters = {"device_id": dev_id}
                if slot_name:
                    slot_filters["name"] = slot_name

                slots = await FRTUSlots.select(**slot_filters)

                for slot in slots:
                    slot_dict = dict(slot)

                    attrs = slot_dict.pop("attribute", {}) or {}
                    for k, v in attrs.items():
                        slot_dict[k] = v

                    slot_dict["id"] = str(slot_dict["id"])
                    slot_dict["deviceName"] = dev_name
                    slot_dict["parentName"] = site_name
                    slot_dict["creationTs"] = int(slot_dict["creation_time"].timestamp() * 1000) if slot_dict.get("creation_time") else None
                    slot_dict["lastUpdateTs"] = int(slot_dict["last_update_time"].timestamp() * 1000) if slot_dict.get("last_update_time") else None

                    response_slots.append(slot_dict)

        if slot_name and response_slots:
            response_slots = [s for s in response_slots if s["name"] == slot_name]

        return {"count": len(response_slots), "slots": response_slots}

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

