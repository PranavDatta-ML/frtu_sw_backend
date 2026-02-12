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
    parameter_found = False

    for slave in slaves:
        params = slave.get("slaveConfig", {}).get("modbusParameters", [])
        new_params = []
        
        for param in params:
            if str(param.get("id")) != parameter_id:
                new_params.append(param)
            else:
                parameter_found = True
        
        slave["slaveConfig"]["modbusParameters"] = new_params

    if not parameter_found:
        raise HTTPException(404, "Parameter not found")

    await FRTUModules.update(
        conditions={"id": module.id},
        channel={"tcpSlaves": slaves},
    )

    await asyncio.to_thread(frtu_client.update_mb_tcp_config, {"modbusSlaves": slaves})

    return {"status": "success", "message": "TCP parameter deleted from DB and mb_conf_tcp.ini"}



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
    new_slaves = []
    found = False
    deleted_params = 0

    for sl in slaves:
        if str(sl.get("id")) == slave_id:
            found = True
            deleted_params += len(sl.get("slaveConfig", {}).get("modbusParameters", []))
            continue
        new_slaves.append(sl)

    if not found:
        raise HTTPException(404, "Slave not found")

    await FRTUModules.update(
        conditions={"id": module.id},
        channel={"tcpSlaves": new_slaves}
    )

    await asyncio.to_thread(frtu_client.update_mb_tcp_config, {"modbusSlaves": new_slaves})

    return {
        "status": "success",
        "deleted_slave_id": slave_id,
        "deleted_parameters_count": deleted_params,
        "remaining_slaves": len(new_slaves)
    }
