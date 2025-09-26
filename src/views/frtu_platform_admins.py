from fastapi import Request

from src.schemas.frtu_platform_admins import FRTUPlatformAdminCreate, FRTUPlatformAdminOut
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.utils.schema import verify_schema

from src import Settings, HttpStatusCode


async def create(request: Request, settings: Settings):
    ok, messages, data = await verify_schema(await request.json(), FRTUPlatformAdminCreate)

    user = getattr(request.state, "user", None)
    if not user:
        return HttpStatusCode.NOT_AUTHENTICATED.response(message="User not authenticated!")

    if not ok:
        return HttpStatusCode.BAD_REQUEST.response(message=messages)

    value = await FRTUPlatformAdmin.insert(**data.dict())

    payload = FRTUPlatformAdminOut.model_validate(value).model_dump(mode="json")
    return HttpStatusCode.CREATED.response(message="FRTU Device created!", data=payload)


async def get(request: Request, settings: Settings):
    pass
