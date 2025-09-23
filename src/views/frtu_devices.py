from fastapi import Request
from src.schemas.frtu_devices import FRTUDeviceCreate, FRTUDeviceUpdate
from src.models.frtu_devices import FRTUDevices
from src.utils.schema import verify_schema

from src import Settings, HttpStatusCode


async def create(request: Request, settings: Settings):
    ok, messages, data = await verify_schema(await request.json(), FRTUDeviceCreate)

    if not ok:
        return HttpStatusCode.BAD_REQUEST.response(message=messages)

    print(data.dict())

    try:
        value = await FRTUDevices.insert(**data.dict())
        return HttpStatusCode.CREATED.response(message="FRTU Device created!", data=value)
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


async def get(request: Request, settings: Settings):
    pass
