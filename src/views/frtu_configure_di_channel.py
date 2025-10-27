import os
from fastapi import Query, Request, Header, Depends
from datetime import datetime, timezone
import uuid

from fastapi.responses import JSONResponse
from src.core.settings import Settings
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_modules import FRTUModules
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_sites import FRTUSites
from src.models.frtu_slots import FRTUSlots
from src.utils.access_token import decode_token
from src.utils.config_parser import parse_devids_conf
from src.utils.ini_handler import  update_ini_file


async def configure_di_channel_remote(
    request: Request,
    frtuname: str = Query(...),
    frtutype: str = Query(...),
    slotnumber: str = Query(...),
    channel: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return JSONResponse(status_code=401, content={"status": "error", "message": f"Tenant token decode failed: {str(e)}"})

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid tenant token: tenant_id missing"})

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Invalid tenant_id in token: {str(e)}"})

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be an integer"})

        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Can only configure channels for slots 4-11"})

        channel_lower = channel.lower()
        if not channel_lower.startswith("di_"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Channel must be in format 'di_X'"})

        try:
            channel_number = int(channel_lower.split("_")[1])
        except:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid channel format"})

        if channel_number < 1 or channel_number > 16:
            return JSONResponse(status_code=400, content={"status": "error", "message": "DI channel must be between di_1 and di_16"})

        payload = await request.json()
        ioa = payload.get("ioa")

        if not ioa:
            return JSONResponse(status_code=400, content={"status": "error", "message": "ioa is required"})

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found for this tenant"})

        project_ids = [p.id for p in projects]
        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})

        site_ids = [s.id for s in sites]
        devices = await FRTUDevices.select(name=frtuname, type=frtutype, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})

        device = devices[0]
        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})

        module = modules[0]
        current_attr = module.get("attribute", {}) or {}
        module_type = current_attr.get("module_type", "").upper()

        if module_type != "DI":
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slotnumber} has {module_type} module, cannot configure DI channel"})

        devids_slot_no = slotnumber - 3
        serial_channel = f"SERIAL_CH{devids_slot_no:02d}"

        try:
            devids_data = parse_devids_conf()
            devids_conf = next((c for c in devids_data if int(c.get("slot_no", -1)) == devids_slot_no), None)
            
            if devids_conf:
                serialport = devids_conf.get("dev_path", "/dev/ttyS1")
                module_id_from_conf = devids_conf.get("module_id", "xxxxxxxxxxxxx")
            else:
                serialport = "/dev/ttyS1"
                module_id_from_conf = "xxxxxxxxxxxxx"
        except:
            serialport = "/dev/ttyS1"
            module_id_from_conf = "xxxxxxxxxxxxx"

        deviceid = current_attr.get("module_id", module_id_from_conf)
        devicetype = "DI"
        status = "ENABLED"

        current_channel = module.get("channel", {}) or {}
        
        channel_key = f"channel_{devids_slot_no:02d}"
        if channel_key not in current_channel:
            current_channel[channel_key] = {}
        
        current_channel[channel_key]["serialport"] = serialport
        current_channel[channel_key]["deviceid"] = deviceid
        current_channel[channel_key]["devicetype"] = devicetype
        current_channel[channel_key]["status"] = status

        if channel_lower not in current_channel[channel_key]:
            current_channel[channel_key][channel_lower] = {}
        
        current_channel[channel_key][channel_lower].update(payload)

        ts = payload.get("ts", "0")
        is_configure = "1"
        
        try:
            update_ini_file(
                module_type, 
                serial_channel, 
                channel_lower, 
                ioa, 
                ts, 
                is_configure,
                serialport=serialport,
                deviceid=deviceid,
                devicetype=devicetype
            )
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Failed to update INI file: {str(e)}"})

        naive_utc_now = datetime.utcnow()
        
        await FRTUModules.update(
            extra={},
            conditions={"id": module["id"]},
            channel=current_channel,
            last_update_time=naive_utc_now
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"DI Channel {channel} configured successfully for slot {slotnumber}",
                "channel_details": {
                    "frtu_name": frtuname,
                    "slot_number": slotnumber,
                    "module_type": module_type,
                    "channel": channel_lower,
                    "serial_channel": serial_channel,
                    "serialport": serialport,
                    "deviceid": deviceid,
                    "devicetype": devicetype,
                    "status": status,
                    "configuration": current_channel[channel_key][channel_lower]
                },
                "ini_file_updated": True
            }
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

async def configure_di_channel_properties(
    request: Request,
    frtuname: str = Query(...),
    frtutype: str = Query(...),
    slotnumber: str = Query(...),
    channel: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        tenant_token = authorization.split(" ")[1]
        tenant_data = decode_token(tenant_token)
        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid tenant token"})
        tenant_id = uuid.UUID(tenant_id_str)

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be integer"})

        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Can only configure properties for slots 4-11"})

        channel_lower = channel.lower()
        if not channel_lower.startswith("di_"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Channel must be in format di_X"})

        payload = await request.json()

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found"})
        project_ids = [p.id for p in projects]

        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})
        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(name=frtuname, type=frtutype, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})

        device = devices[0]
        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})

        module = modules[0]
        attr = module.get("attribute", {}) or {}
        module_type = attr.get("module_type", "").upper()

        if module_type != "DI":
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slotnumber} has {module_type}, not DI"})

        channel_data = module.get("channel", {}) or {}
        channel_key = f"channel_{slotnumber - 3:02d}"

        if channel_key not in channel_data:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No channels configured in slot {slotnumber}. Configure remote channel first."})

        if channel_lower not in channel_data[channel_key]:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Channel '{channel_lower}' not configured yet. Configure remote channel first."})

        channel_data[channel_key][channel_lower].update(payload)

        naive_utc_now = datetime.utcnow()
        await FRTUModules.update(
            extra={},
            conditions={"id": module["id"]},
            channel=channel_data,
            last_update_time=naive_utc_now
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"DI Channel properties configured successfully for {channel_lower} at slot {slotnumber}",
                "updated_properties": payload
            },
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})




async def configure_do_channel_remote(
    request: Request,
    frtuname: str = Query(...),
    frtutype: str = Query(...),
    slotnumber: str = Query(...),
    channel: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        tenant_token = authorization.split(" ")[1]
        tenant_data = decode_token(tenant_token)
        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid tenant token"})
        tenant_id = uuid.UUID(tenant_id_str)

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be an integer"})

        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Can only configure channels for slots 4-11"})

        channel_lower = channel.lower()
        if not channel_lower.startswith("do_"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Channel must be in format 'do_X'"})

        try:
            channel_number = int(channel_lower.split("_")[1])
        except:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid channel format"})

        if channel_number < 1 or channel_number > 10:
            return JSONResponse(status_code=400, content={"status": "error", "message": "DO channel must be between do_1 and do_10"})

        payload = await request.json()
        ioa = payload.get("ioa")

        if not ioa:
            return JSONResponse(status_code=400, content={"status": "error", "message": "ioa is required"})

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found"})
        project_ids = [p.id for p in projects]

        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})
        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(name=frtuname, type=frtutype, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})

        device = devices[0]
        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})

        module = modules[0]
        current_attr = module.get("attribute", {}) or {}
        module_type = current_attr.get("module_type", "").upper()

        if module_type != "DO":
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slotnumber} has {module_type} module, cannot configure DO channel"})

        devids_slot_no = slotnumber - 3
        serial_channel = f"SERIAL_CH{devids_slot_no:02d}"

        try:
            devids_data = parse_devids_conf()
            devids_conf = next((c for c in devids_data if int(c.get("slot_no", -1)) == devids_slot_no), None)
            
            if devids_conf:
                serialport = devids_conf.get("dev_path", "/dev/ttyS1")
                module_id_from_conf = devids_conf.get("module_id", "xxxxxxxxxxxxx")
            else:
                serialport = "/dev/ttyS1"
                module_id_from_conf = "xxxxxxxxxxxxx"
        except:
            serialport = "/dev/ttyS1"
            module_id_from_conf = "xxxxxxxxxxxxx"

        deviceid = current_attr.get("module_id", module_id_from_conf)
        devicetype = "DO"
        status = "ENABLED"

        current_channel = module.get("channel", {}) or {}
        
        channel_key = f"channel_{devids_slot_no:02d}"
        if channel_key not in current_channel:
            current_channel[channel_key] = {}
        
        current_channel[channel_key]["serialport"] = serialport
        current_channel[channel_key]["deviceid"] = deviceid
        current_channel[channel_key]["devicetype"] = devicetype
        current_channel[channel_key]["status"] = status

        if channel_lower not in current_channel[channel_key]:
            current_channel[channel_key][channel_lower] = {}
        
        current_channel[channel_key][channel_lower].update(payload)

        ts = payload.get("ts", "0")
        is_configure = "1"
        
        try:
            update_ini_file(
                module_type, 
                serial_channel, 
                channel_lower, 
                ioa, 
                ts, 
                is_configure,
                serialport=serialport,
                deviceid=deviceid,
                devicetype=devicetype
            )
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Failed to update INI file: {str(e)}"})

        naive_utc_now = datetime.utcnow()
        
        await FRTUModules.update(
            extra={},
            conditions={"id": module["id"]},
            channel=current_channel,
            last_update_time=naive_utc_now
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"DO Channel {channel} configured successfully for slot {slotnumber}",
                "channel_details": {
                    "frtu_name": frtuname,
                    "slot_number": slotnumber,
                    "module_type": module_type,
                    "channel": channel_lower,
                    "serial_channel": serial_channel,
                    "serialport": serialport,
                    "deviceid": deviceid,
                    "devicetype": devicetype,
                    "status": status,
                    "configuration": current_channel[channel_key][channel_lower]
                },
                "ini_file_updated": True
            }
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

async def configure_do_channel_properties(
    request: Request,
    frtuname: str = Query(...),
    frtutype: str = Query(...),
    slotnumber: str = Query(...),
    channel: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        tenant_token = authorization.split(" ")[1]
        tenant_data = decode_token(tenant_token)
        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid tenant token"})
        tenant_id = uuid.UUID(tenant_id_str)

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be integer"})

        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Can only configure properties for slots 4-11"})

        channel_lower = channel.lower()
        if not channel_lower.startswith("do_"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Channel must be in format do_X"})

        payload = await request.json()

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found"})
        project_ids = [p.id for p in projects]

        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})
        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(name=frtuname, type=frtutype, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})

        device = devices[0]
        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})

        module = modules[0]
        attr = module.get("attribute", {}) or {}
        module_type = attr.get("module_type", "").upper()

        if module_type != "DO":
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slotnumber} has {module_type}, not DO"})

        channel_data = module.get("channel", {}) or {}
        channel_key = f"channel_{slotnumber - 3:02d}"

        if channel_key not in channel_data:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No channels configured in slot {slotnumber}. Configure remote channel first."})

        if channel_lower not in channel_data[channel_key]:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Channel '{channel_lower}' not configured yet. Configure remote channel first."})

        channel_data[channel_key][channel_lower].update(payload)

        naive_utc_now = datetime.utcnow()
        await FRTUModules.update(
            extra={},
            conditions={"id": module["id"]},
            channel=channel_data,
            last_update_time=naive_utc_now
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"DO Channel properties configured successfully for {channel_lower} at slot {slotnumber}",
                "updated_properties": payload
            },
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})



async def update_di_channel_remote(
    request: Request,
    frtuname: str = Query(...),
    frtutype: str = Query(...),
    slotnumber: int = Query(...),
    channel: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        token = authorization.split(" ")[1]
        tenant_data = decode_token(token)
        tenant_id = uuid.UUID(tenant_data.get("tenant_id"))

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be integer"})

        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Slotnumber must be between 4 and 11"})
        channel_lower = channel.lower()
        if not channel_lower.startswith("di_"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Channel must be in format di_X"})

        payload = await request.json()
        if not payload:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Payload cannot be empty"})

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found"})
        project_ids = [p.id for p in projects]

        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})
        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(name=frtuname, type=frtutype, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})
        device = devices[0]

        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})
        module = modules[0]

        attr = module.get("attribute", {}) or {}
        module_type = attr.get("module_type", "").upper()
        if module_type != "DI":
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slotnumber} has {module_type} module, not DI"})

        channel_data = module.get("channel", {}) or {}
        channel_key = f"channel_{slotnumber - 3:02d}"

        if channel_key not in channel_data or channel_lower not in channel_data[channel_key]:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Channel '{channel_lower}' not configured yet"})

        channel_data[channel_key][channel_lower].update(payload)

        ioa = channel_data[channel_key][channel_lower].get("ioa", payload.get("ioa", ""))
        ts = channel_data[channel_key][channel_lower].get("ts", payload.get("ts", "0"))
        serial_channel = f"SERIAL_CH{slotnumber - 3:02d}"
        serialport = channel_data[channel_key].get("serialport", "/dev/ttyS1")
        deviceid = channel_data[channel_key].get("deviceid", "xxxxxxxxxxxxx")
        devicetype = channel_data[channel_key].get("devicetype", "DI")
        is_configure = "1"

        try:
            update_ini_file(
                module_type,
                serial_channel,
                channel_lower,
                ioa,
                ts,
                is_configure,
                serialport=serialport,
                deviceid=deviceid,
                devicetype=devicetype
            )
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Failed to update INI file: {str(e)}"})

        await FRTUModules.update(
            extra={},
            conditions={"id": module["id"]},
            channel=channel_data,
            last_update_time=datetime.utcnow()
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"DI Channel {channel_lower} updated successfully for slot {slotnumber}",
                "updated_data": payload,
                "ini_file_updated": True
            }
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

async def update_di_channel_properties(
    request: Request,
    frtuname: str = Query(...),
    frtutype: str = Query(...),
    slotnumber: int = Query(...),
    channel: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        token = authorization.split(" ")[1]
        tenant_data = decode_token(token)
        tenant_id = uuid.UUID(tenant_data.get("tenant_id"))

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be integer"})

        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Slotnumber must be between 4 and 11"})
        channel_lower = channel.lower()
        if not channel_lower.startswith("di_"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Channel must be in format di_X"})

        payload = await request.json()
        if not payload:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Payload cannot be empty"})

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found"})
        project_ids = [p.id for p in projects]

        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})
        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(name=frtuname, type=frtutype, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})
        device = devices[0]

        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})
        module = modules[0]

        attr = module.get("attribute", {}) or {}
        module_type = attr.get("module_type", "").upper()
        if module_type != "DI":
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slotnumber} has {module_type} module, not DI"})

        channel_data = module.get("channel", {}) or {}
        channel_key = f"channel_{slotnumber - 3:02d}"

        if channel_key not in channel_data or channel_lower not in channel_data[channel_key]:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Channel '{channel_lower}' not configured yet"})

        channel_data[channel_key][channel_lower].update(payload)

        serial_channel = f"SERIAL_CH{slotnumber - 3:02d}"
        serialport = channel_data[channel_key].get("serialport", "/dev/ttyS1")
        deviceid = channel_data[channel_key].get("deviceid", "xxxxxxxxxxxxx")
        devicetype = channel_data[channel_key].get("devicetype", "DI")
        ioa = channel_data[channel_key][channel_lower].get("ioa", "0")
        ts = channel_data[channel_key][channel_lower].get("ts", "0")
        is_configure = "1"

        try:
            update_ini_file(
                module_type,
                serial_channel,
                channel_lower,
                ioa,
                ts,
                is_configure,
                serialport=serialport,
                deviceid=deviceid,
                devicetype=devicetype
            )
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Failed to update INI file: {str(e)}"})

        await FRTUModules.update(
            extra={},
            conditions={"id": module["id"]},
            channel=channel_data,
            last_update_time=datetime.utcnow()
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"DI Channel properties updated successfully for {channel_lower} (slot {slotnumber})",
                "updated_properties": payload,
                "ini_file_updated": True
            }
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})



async def update_do_channel_remote(
    request: Request,
    frtuname: str = Query(...),
    frtutype: str = Query(...),
    slotnumber: int = Query(...),
    channel: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})
        token = authorization.split(" ")[1]
        tenant_data = decode_token(token)
        tenant_id = uuid.UUID(tenant_data.get("tenant_id"))

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be integer"})
        
        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Slotnumber must be between 4 and 11"})
        channel_lower = channel.lower()
        if not channel_lower.startswith("do_"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Channel must be in format do_X"})

        payload = await request.json()
        if not payload:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Payload cannot be empty"})

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found"})
        project_ids = [p.id for p in projects]

        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})
        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(name=frtuname, type=frtutype, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})
        device = devices[0]

        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})
        slot = slots[slotnumber - 1]

        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})
        module = modules[0]

        attr = module.get("attribute", {}) or {}
        module_type = attr.get("module_type", "").upper()
        if module_type != "DO":
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slotnumber} has {module_type} module, not DO"})

        channel_data = module.get("channel", {}) or {}
        channel_key = f"channel_{slotnumber - 3:02d}"

        if channel_key not in channel_data or channel_lower not in channel_data[channel_key]:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Channel '{channel_lower}' not configured yet"})

        channel_data[channel_key][channel_lower].update(payload)

        ioa = channel_data[channel_key][channel_lower].get("ioa", payload.get("ioa", ""))
        ts = channel_data[channel_key][channel_lower].get("ts", payload.get("ts", "0"))
        serial_channel = f"SERIAL_CH{slotnumber - 3:02d}"
        serialport = channel_data[channel_key].get("serialport", "/dev/ttyS1")
        deviceid = channel_data[channel_key].get("deviceid", "xxxxxxxxxxxxx")
        devicetype = "DO"
        is_configure = "1"

        try:
            update_ini_file(
                module_type,
                serial_channel,
                channel_lower,
                ioa,
                ts,
                is_configure,
                serialport=serialport,
                deviceid=deviceid,
                devicetype=devicetype
            )
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Failed to update .ini file: {str(e)}"})

        await FRTUModules.update(
            extra={},
            conditions={"id": module["id"]},
            channel=channel_data,
            last_update_time=datetime.utcnow()
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"DO Channel {channel_lower} updated successfully for slot {slotnumber}",
                "updated_data": payload,
                "ini_file_updated": True
            }
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


async def update_do_channel_properties(
    request: Request,
    frtuname: str = Query(...),
    frtutype: str = Query(...),
    slotnumber: int = Query(...),
    channel: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})
        token = authorization.split(" ")[1]
        tenant_data = decode_token(token)
        tenant_id = uuid.UUID(tenant_data.get("tenant_id"))

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be integer"})
        
        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Slotnumber must be between 4 and 11"})
        channel_lower = channel.lower()
        if not channel_lower.startswith("do_"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Channel must be in format do_X"})

        payload = await request.json()
        if not payload:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Payload cannot be empty"})

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found"})
        project_ids = [p.id for p in projects]

        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})
        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(name=frtuname, type=frtutype, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})
        device = devices[0]

        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})
        slot = slots[slotnumber - 1]

        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})
        module = modules[0]

        attr = module.get("attribute", {}) or {}
        module_type = attr.get("module_type", "").upper()
        if module_type != "DO":
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slotnumber} has {module_type} module, not DO"})

        channel_data = module.get("channel", {}) or {}
        channel_key = f"channel_{slotnumber - 3:02d}"
        if channel_key not in channel_data or channel_lower not in channel_data[channel_key]:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Channel '{channel_lower}' not configured yet"})

        channel_data[channel_key][channel_lower].update(payload)

        ioa = channel_data[channel_key][channel_lower].get("ioa", payload.get("ioa", ""))
        ts = channel_data[channel_key][channel_lower].get("ts", payload.get("ts", "0"))
        serial_channel = f"SERIAL_CH{slotnumber - 3:02d}"
        serialport = channel_data[channel_key].get("serialport", "/dev/ttyS1")
        deviceid = channel_data[channel_key].get("deviceid", "xxxxxxxxxxxxx")
        devicetype = "DO"
        is_configure = "1"

        try:
            update_ini_file(
                module_type,
                serial_channel,
                channel_lower,
                ioa,
                ts,
                is_configure,
                serialport=serialport,
                deviceid=deviceid,
                devicetype=devicetype
            )
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Failed to update .ini file: {str(e)}"})

        await FRTUModules.update(
            extra={},
            conditions={"id": module["id"]},
            channel=channel_data,
            last_update_time=datetime.utcnow()
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"DO Channel properties updated successfully for {channel_lower} (slot {slotnumber})",
                "updated_properties": payload,
                "ini_file_updated": True
            }
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


async def get_di_channel_detail(
    request: Request,
    frtuname: str = Query(...),
    slotnumber: str = Query(...),
    channel: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return JSONResponse(status_code=401, content={"status": "error", "message": f"Tenant token decode failed: {str(e)}"})

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid tenant token: tenant_id missing"})

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Invalid tenant_id in token: {str(e)}"})

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be an integer"})

        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Can only get channel details for slots 4-11"})

        channel_lower = channel.lower()
        if not channel_lower.startswith("di_"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Channel must be in format 'di_X'"})

        try:
            channel_number = int(channel_lower.split("_")[1])
        except:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid channel format"})

        if channel_number < 1 or channel_number > 16:
            return JSONResponse(status_code=400, content={"status": "error", "message": "DI channel must be between di_1 and di_16"})

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found for this tenant"})

        project_ids = [p.id for p in projects]
        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})

        site_ids = [s.id for s in sites]
        devices = await FRTUDevices.select(name=frtuname, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})

        device = devices[0]
        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})

        module = modules[0]
        current_attr = module.get("attribute", {}) or {}
        module_type = current_attr.get("module_type", "").upper()

        if module_type != "DI":
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slotnumber} has {module_type} module, not DI"})

        channel_data = module.get("channel", {}) or {}
        devids_slot_no = slotnumber - 3
        channel_key = f"channel_{devids_slot_no:02d}"

        if channel_key not in channel_data:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No channels configured in slot {slotnumber}"})

        if channel_lower not in channel_data[channel_key]:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Channel '{channel_lower}' not configured yet"})

        channel_config = channel_data[channel_key][channel_lower]

        general_info = {
            "id": channel_config.get("id", ""),
            "name": channel_config.get("name", ""),
            "description": channel_config.get("description", ""),
            "high_level_filter": channel_config.get("high_level_filter", ""),
            "low_level_filter": channel_config.get("low_level_filter", "")
        }

        time_stamp = channel_config.get("time_stamp", "0")
        inverse = channel_config.get("inverse", "0")

        channel_info = {
            "channel_type": channel_config.get("channel_type", ""),
            "DI_input": channel_config.get("DI_input", channel_lower),
            "time_stamp": "Enabled" if time_stamp == "1" else "Disabled",
            "inverse": "Enabled" if inverse == "1" else "Disabled",
            "off_delay": channel_config.get("off_delay", ""),
            "on_delay": channel_config.get("on_delay", ""),
            "tag_name": channel_config.get("tag_name", "")
        }

        response_data = {
            "general_info": general_info,
            "channel_info": channel_info
        }

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"DI Channel {channel} details retrieved successfully",
                # "data": response_data
                "general_info": general_info,
                "channel_info": channel_info
            }
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


async def get_do_channel_detail(
    request: Request,
    frtuname: str = Query(...),
    slotnumber: str = Query(...),
    channel: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return JSONResponse(status_code=401, content={"status": "error", "message": f"Tenant token decode failed: {str(e)}"})

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid tenant token: tenant_id missing"})

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Invalid tenant_id in token: {str(e)}"})

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be an integer"})

        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Can only get channel details for slots 4-11"})

        channel_lower = channel.lower()
        if not channel_lower.startswith("do_"):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Channel must be in format 'do_X'"})

        try:
            channel_number = int(channel_lower.split("_")[1])
        except:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid channel format"})

        if channel_number < 1 or channel_number > 10:
            return JSONResponse(status_code=400, content={"status": "error", "message": "DO channel must be between do_1 and do_10"})

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found for this tenant"})

        project_ids = [p.id for p in projects]
        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})

        site_ids = [s.id for s in sites]
        devices = await FRTUDevices.select(name=frtuname, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})

        device = devices[0]
        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})

        module = modules[0]
        current_attr = module.get("attribute", {}) or {}
        module_type = current_attr.get("module_type", "").upper()

        if module_type != "DO":
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slotnumber} has {module_type} module, not DO"})

        channel_data = module.get("channel", {}) or {}
        devids_slot_no = slotnumber - 3
        channel_key = f"channel_{devids_slot_no:02d}"

        if channel_key not in channel_data:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No channels configured in slot {slotnumber}"})

        if channel_lower not in channel_data[channel_key]:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Channel '{channel_lower}' not configured yet"})

        channel_config = channel_data[channel_key][channel_lower]

        general_info = {
            "id": channel_config.get("id", ""),
            "name": channel_config.get("name", ""),
            "description": channel_config.get("description", ""),
            "pulse_time": channel_config.get("pulse_time", "")
        }

        channel_info = {
            "channel_type": channel_config.get("channel_type", ""),
            "DO_output": channel_config.get("DO_output", channel_lower),
            "tag_name": channel_config.get("tag_name", "")
        }

        response_data = {
            "general_info": general_info,
            "channel_info": channel_info
        }

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"DO Channel {channel} details retrieved successfully",
                # "data": response_data
                "general_info": general_info,
                "channel_info": channel_info
            }
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


async def get_all_channels_by_slot(
    request: Request,
    frtuname: str = Query(...),
    slotnumber: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return JSONResponse(status_code=401, content={"status": "error", "message": f"Tenant token decode failed: {str(e)}"})

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid tenant token: tenant_id missing"})

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Invalid tenant_id in token: {str(e)}"})

        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slotnumber must be an integer"})

        if slotnumber < 4 or slotnumber > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Can only get channels for slots 4-11"})

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found for this tenant"})

        project_ids = [p.id for p in projects]
        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found"})

        site_ids = [s.id for s in sites]
        devices = await FRTUDevices.select(name=frtuname, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtuname}' not found"})

        device = devices[0]
        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})

        module = modules[0]
        current_attr = module.get("attribute", {}) or {}
        module_type = current_attr.get("module_type", "").upper()

        channel_data = module.get("channel", {}) or {}
        devids_slot_no = slotnumber - 3
        channel_key = f"channel_{devids_slot_no:02d}"

        if channel_key not in channel_data:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No channels configured in slot {slotnumber}"})

        serial_channel = f"SERIAL_CH{devids_slot_no:02d}"
        
        channels_list = []
        for ch_name, ch_config in channel_data[channel_key].items():
            if ch_name.startswith("di_") or ch_name.startswith("do_"):
                channels_list.append({
                    "channel_name": ch_name,
                    "configuration": ch_config
                })

        response_data = {
            "frtu_name": frtuname,
            "slot_number": slotnumber,
            "module_type": module_type,
            "serial_channel": serial_channel,
            "serialport": channel_data[channel_key].get("serialport", ""),
            "deviceid": channel_data[channel_key].get("deviceid", ""),
            "devicetype": channel_data[channel_key].get("devicetype", ""),
            "status": channel_data[channel_key].get("status", ""),
            "total_channels": len(channels_list),
            "channels": channels_list
        }

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"All channels for slot {slotnumber} retrieved successfully",
                "data": response_data
            }
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})









