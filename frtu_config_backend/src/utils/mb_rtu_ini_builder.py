from typing import List
from uuid import UUID, uuid4

from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.schemas.frtu_modbus_rtu import ModbusPayload
from src.utils.frtu_client import frtu_client


def build_mb_ini_payload(payload):
    return {
        "slot_number": payload.slotInfo.slotNumber,
        "protocol": payload.categoryInfo.communicationProtocol,
        "channels": payload.categoryInfo.channels
    }

def normalize_param_config(pc: dict):
    fc = pc.get("readFunctionCode", "").upper().replace("FC", "")
    pc["readFunctionCode"] = fc

    dt = pc.get("dataType", "").upper().replace(" ", "_")
    if not dt.startswith("DT_"):
        dt = f"DT_{dt}"
    pc["dataType"] = dt

    pc["endianness"] = pc.get("endianness", "").replace(" ", "_").upper()
    return pc

async def merge_modbus_data(existing_channels: List[dict], new_payload: ModbusPayload) -> List[dict]:
    channel_map = {str(ch.get("id")): ch for ch in existing_channels}
    
    for new_ch in new_payload.categoryInfo.channels or []:
        ch_dict = new_ch.model_dump(mode="json")
        ch_id = str(ch_dict["id"])
        
        if ch_id in channel_map:
            old_ch = channel_map[ch_id]
            old_ch.update(ch_dict)
            old_slave_map = {str(sl.get("id")): sl for sl in old_ch["channelConfig"]["modbusSlaves"]}
            for new_sl in ch_dict["channelConfig"]["modbusSlaves"]:
                sl_id = str(new_sl["id"])
                if sl_id in old_slave_map:
                    old_slave = old_slave_map[sl_id]
                    old_param_map = {str(p.get("id")): p for p in old_slave["slaveConfig"]["modbusParameters"]}
                    for new_p in new_sl["slaveConfig"]["modbusParameters"]:
                        p_id = str(new_p["id"])
                        if p_id in old_param_map:
                            old_param_map[p_id].update(new_p)
                        else:
                            old_slave["slaveConfig"]["modbusParameters"].append(new_p)
                else:
                    old_ch["channelConfig"]["modbusSlaves"].append(new_sl)
        else:
            channel_map[ch_id] = ch_dict
    
    return list(channel_map.values())

async def handle_modbus_rtu(device_id: str, device_type: str, payload: ModbusPayload, user_id: UUID):
    device_uuid = UUID(device_id)
    device = (await FRTUDevices.select(id=device_uuid))[0]

    if device.type.name.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    channels = payload.categoryInfo.channels or []
    if not channels:
        raise HTTPException(400, "At least one Modbus RTU channel required")

    for ch in channels:
        if not ch.id or str(ch.id).strip() == "":
            ch.id = uuid4()

        for sl in ch.channelConfig.modbusSlaves:
            if not sl.id or str(sl.id).strip() == "":
                sl.id = uuid4()

            for p in sl.slaveConfig.modbusParameters:
                if not p.id or str(p.id).strip() == "":
                    p.id = uuid4()
                p.parameterConfig = normalize_param_config(p.parameterConfig.model_dump())

    attribute = {
        "slotInfo": payload.slotInfo.model_dump(),
        "protocol": "RTU"
    }

    channel_data = {
        "channels": [c.model_dump(mode="json") for c in channels]
    }

    existing = await FRTUModules.select(slot_id=payload.slotInfo.slotId)

    if existing:
        await FRTUModules.update(
            conditions={"id": existing[0].id},
            attribute=attribute,
            channel=channel_data
        )
        module_id = existing[0].id
    else:
        obj = await FRTUModules.insert(
            slot_id=payload.slotInfo.slotId,
            module_type=(await FRTUModuleType.select(name="COM"))[0].id,
            attribute=attribute,
            channel=channel_data
        )
        module_id = obj.id

    frtu_client.update_mb_config(build_mb_ini_payload(payload))

    return {"status": "success", "moduleId": str(module_id)}


async def handle_modbus_tcp(device_id: str, device_type: str, payload: ModbusPayload, user_id: UUID):
    device_uuid = UUID(device_id)
    device = (await FRTUDevices.select(id=device_uuid))[0]

    if device.type.name.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    slaves = payload.categoryInfo.modbusSlaves or []
    if not slaves:
        raise HTTPException(400, "At least one Modbus TCP slave required")

    for sl in slaves:
        if not sl.id or str(sl.id).strip() == "":
            sl.id = uuid4()

        for p in sl.slaveConfig.modbusParameters:
            if not p.id or str(p.id).strip() == "":
                p.id = uuid4()
            p.parameterConfig = normalize_param_config(p.parameterConfig.model_dump())

    attribute = {
        "slotInfo": payload.slotInfo.model_dump(),
        "protocol": "TCP"
    }

    channel_data = {
        "tcpSlaves": [s.model_dump(mode="json") for s in slaves]
    }

    existing = await FRTUModules.select(slot_id=payload.slotInfo.slotId)

    if existing:
        await FRTUModules.update(
            conditions={"id": existing[0].id},
            attribute=attribute,
            channel=channel_data
        )
        module_id = existing[0].id
    else:
        obj = await FRTUModules.insert(
            slot_id=payload.slotInfo.slotId,
            module_type=(await FRTUModuleType.select(name="COM"))[0].id,
            attribute=attribute,
            channel=channel_data
        )
        module_id = obj.id

    frtu_client.update_mb_tcp_config({"modbusSlaves": channel_data["tcpSlaves"]})

    return {"status": "success", "moduleId": str(module_id)}
