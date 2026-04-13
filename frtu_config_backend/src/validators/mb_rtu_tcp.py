import asyncio
from uuid import UUID
from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_modules import FRTUModules
from src.utils.frtu_client import frtu_client


async def _delete_rtu_parameter(module, parameter_id: str):
    channels = module.channel.get("channels", [])
    found = False

    for ch in channels:
        ch_no = ch["channelConfig"]["channelNo"]
        slaves = ch["channelConfig"].get("modbusSlaves", [])

        for s_idx, sl in enumerate(slaves, start=1):
            params = sl["slaveConfig"].get("modbusParameters", [])

            for p_idx, p in enumerate(params, start=1):
                if str(p["id"]) == parameter_id:
                    frtu_client.delete_modbus_param(ch_no, s_idx, p_idx)
                    params.pop(p_idx - 1)
                    found = True
                    break
            if found:
                break
        if found:
            break

    if not found:
        raise HTTPException(404, "Parameter not found")

    await FRTUModules.update(conditions={"id": module.id}, channel={"channels": channels})

    return {"status": "success", "message": "RTU parameter deleted from DB and mb_config.ini"}

async def _delete_tcp_parameter(module, parameter_id: str):
    slaves = module.channel.get("tcpSlaves", [])

    for s_idx, slave in enumerate(slaves, start=1):
        params = slave["slaveConfig"]["modbusParameters"]

        for p_idx, p in enumerate(params, start=1):
            if str(p["id"]) == parameter_id:

                await asyncio.to_thread(
                    frtu_client.delete_mb_tcp_param,
                    s_idx,
                    p_idx
                )

                params.pop(p_idx - 1)

                await FRTUModules.update(
                    conditions={"id": module.id},
                    channel={"tcpSlaves": slaves}
                )

                return {
                    "status": "success", 
                    "message": "TCP parameter deleted from DB and mb_config.ini", 
                    "deleted_parameter_id": parameter_id, 
                    "remaining_parameters": len(params), 
                    "slave_id": slave.get("id")
                }

    raise HTTPException(404, "Parameter not found")

async def _delete_rtu_slave(module, slave_id: str):
    channels = module.channel.get("channels", [])
    found = False

    for ch in channels:
        ch_no = ch["channelConfig"]["channelNo"]
        slaves = ch["channelConfig"].get("modbusSlaves", [])

        for s_idx, sl in enumerate(slaves, start=1):
            if str(sl["id"]) == slave_id:
                frtu_client.delete_modbus_slave(ch_no, s_idx)
                slaves.pop(s_idx - 1)
                found = True
                break
        if found:
            break

    if not found:
        raise HTTPException(404, "Slave not found")

    await FRTUModules.update(conditions={"id": module.id}, channel={"channels": channels})

    return {
        "status": "success",
        "message": "RTU slave and its parameters deleted from DB and mb_config.ini"
    }

async def _delete_tcp_slave(module, slave_id: str):
    slaves = module.channel.get("tcpSlaves", [])

    for s_idx, slave in enumerate(slaves, start=1):
        if str(slave["id"]) == slave_id:

            await asyncio.to_thread(
                frtu_client.delete_mb_tcp_slave,
                s_idx
            )

            slaves.pop(s_idx - 1)

            await FRTUModules.update(
                conditions={"id": module.id},
                channel={"tcpSlaves": slaves}
            )

    return {
        "status": "success",
        "deleted_slave_id": slave_id,
        "deleted_parameters_count": len(slave.get("slaveConfig", {}).get("modbusParameters", [])),
        "remaining_slaves": len(slaves)
    }
