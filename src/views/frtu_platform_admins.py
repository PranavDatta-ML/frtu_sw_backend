from fastapi import Request
from src.schemas.frtu_platform_admins import FRTUPlatformAdminCreate
from src.models.frtu_devices import FRTUDevices
from src.utils.schema import verify_schema

from src import Settings, HttpStatusCode


async def create(request: Request, settings: Settings):
    ok, messages, data = await verify_schema(await request.json(), FRTUPlatformAdminCreate)

    if not ok:
        return HttpStatusCode.BAD_REQUEST.response(message=messages)

    print(dir(data))

    value = await FRTUDevices.insert(**data.to_orm())
    return HttpStatusCode.CREATED.response(message="FRTU Device created!", data=value)


async def get(request: Request, settings: Settings):
    pass
