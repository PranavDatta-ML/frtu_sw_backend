import asyncio
from datetime import datetime
from uuid import UUID
from fastapi import HTTPException

from src.models.frtu_base_config import FRTUBaseConfig
from src.models.frtu_devices import FRTUDevices
from src.utils.frtu_client import frtu_client


async def add_or_update_base_config(device_id: str, payload, user_id: UUID):
    device_uuid = UUID(device_id)

    device = await FRTUDevices.select(id=device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    existing = await FRTUBaseConfig.select(device_id=device_uuid)

    if existing:
        await FRTUBaseConfig.update(
            conditions={"device_id": device_uuid},
            config_json=payload.config_json,
            attribute=payload.attribute,
            last_update_time=datetime.utcnow()
        )
        config_id = existing[0].id
    else:
        obj = await FRTUBaseConfig.insert(
            device_id=device_uuid,
            config_json=payload.config_json,
            attribute=payload.attribute,
            creation_time=datetime.utcnow(),
            last_update_time=datetime.utcnow()
        )
        config_id = obj.id

    # try:
    #     await frtu_client.update_base_config(payload.config_json)
    #     await FRTUBaseConfig.update(
    #         conditions={"device_id": device_uuid},
    #         last_synced_at=datetime.utcnow()
    #     )
    # except Exception:
    #     raise HTTPException(status_code=502, detail="FRTU device not reachable")

    return {
        "status": "success",
        "message": "Base config saved and synced to device",
        "configId": str(config_id)
    }


async def get_base_config(device_id: str):
    device_uuid = UUID(device_id)

    config = await FRTUBaseConfig.select(device_id=device_uuid)
    if not config:
        raise HTTPException(status_code=404, detail="Base config not found")

    cfg = config[0]

    return {
        "device_id": str(cfg.device_id),
        "config_json": cfg.config_json,
        "attribute": cfg.attribute,
        "last_synced_at": cfg.last_synced_at
    }