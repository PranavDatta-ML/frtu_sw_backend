import asyncio
from typing import Any, Dict, List
from uuid import UUID
from fastapi import HTTPException, status
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_master import FRTUModuleMaster
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_di_module import ConfigureDIModule, ConfigureDIModuleRequest
from src.utils.frtu_client import frtu_client

# =========== Working code to add di module without general info ===========
async def add_di_module(
    device_id: str,
    device_type: str,
    payload: ConfigureDIModule,
    user_id: UUID,
):
    if payload.slot_id is None:
        raise HTTPException(status_code=400, detail="slot_id is required to add a module")
    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    device = devices[0]
    db_type = (
        device.type.name
        if hasattr(device.type, "name")
        else (device.type.value if hasattr(device.type, "value") else str(device.type))
    )
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match for this device_id")

    requested_type = payload.module_type.strip().upper()
    if requested_type not in ("DI", "DO"):
        raise HTTPException(status_code=400, detail="Only DI/DO modules can be added with this API")

    masters = await FRTUModuleMaster.select(id=payload.module_id)
    if not masters:
        raise HTTPException(status_code=400, detail="Invalid module_id")
    master = masters[0]
    master_name = master.name.strip().upper()
    if requested_type == "DI" and "DIGITAL INPUT" not in master_name:
        raise HTTPException(status_code=400, detail="module_type DI must be used with Digital Input module_id")
    if requested_type == "DO" and "DIGITAL OUTPUT" not in master_name:
        raise HTTPException(status_code=400, detail="module_type DO must be used with Digital Output module_id")

    slots = await FRTUSlots.select(id=payload.slot_id, device_id=device_uuid)
    if not slots:
        raise HTTPException(status_code=400, detail="Given slot_id does not belong to this device")
    slot = slots[0]
    try:
        slot_number = int(str(slot.name))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid slot name format in frtu_slots")

    existing = await FRTUModules.select(slot_id=payload.slot_id)
    if existing:
        raise HTTPException(status_code=400, detail="Slot already occupied")

    mtypes = await FRTUModuleType.select(name=requested_type)
    if not mtypes:
        raise HTTPException(status_code=400, detail="Invalid module_type")
    mtype = mtypes[0]

    # === BUILD ATTRIBUTE WITH general_info ===
    info_key = "module_di_info" if requested_type == "DI" else "module_do_info"
    general_info = payload.general_info or {}
    
    # Ensure required fields in general_info
    general_info["slot_number"] = slot_number
    general_info["slot_id"] = str(payload.slot_id)
    # general_info["module_name"] = master.name
    general_info["module_type"] = requested_type

    module_info = {
        "general_info": general_info
    }
    
    full_attribute = {
        "device_id": str(device_uuid),
        "slot_number": slot_number,
        info_key: module_info
    }

    try:
        placed = await FRTUModules.insert(
            slot_id=payload.slot_id,
            name=master.name,
            module_type=mtype.id,
            description=getattr(master, "description", "") or "",
            attribute=full_attribute,
            channel=None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save module: {e}")

    try:
        await asyncio.to_thread(
            frtu_client.update_devids_conf,
            slot_number,
            requested_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Module saved but failed to update devids.conf: {e}",
        )

    return {
        "status": "success",
        "http_code": 201,
        "message": "DI/DO module added successfully with general_info",
        "data": {
            "module_id": str(placed.id),
            "slot_id": str(placed.slot_id),
            "module_type": requested_type,
            # "name": master.name,
            "general_info": general_info,
        },
    }

#=========== Working code to add di module with general info ===========
# async def add_di_module(
#     device_id: str,
#     device_type: str,
#     payload: ConfigureDIModuleRequest,
#     user_id: UUID,
# ):
#     if payload.slot_id is None:
#         raise HTTPException(status_code=400, detail="slot_id is required to add a module")
#     try:
#         device_uuid = UUID(device_id)
#     except Exception:
#         raise HTTPException(status_code=400, detail="Invalid device_id format")

#     devices = await FRTUDevices.select(id=device_uuid)
#     if not devices:
#         raise HTTPException(status_code=400, detail="Invalid device_id")
#     device = devices[0]
#     db_type = (
#         device.type.name
#         if hasattr(device.type, "name")
#         else (device.type.value if hasattr(device.type, "value") else str(device.type))
#     )
#     if db_type.strip().upper() != device_type.strip().upper():
#         raise HTTPException(status_code=400, detail="Device type does not match for this device_id")

#     requested_type = payload.module_type.strip().upper()
#     if requested_type not in ("DI", "DO"):
#         raise HTTPException(status_code=400, detail="Only DI/DO modules can be added with this API")

#     masters = await FRTUModuleMaster.select(id=payload.module_id)
#     if not masters:
#         raise HTTPException(status_code=400, detail="Invalid module_id")
#     master = masters[0]
#     master_name = str(master.name).strip().upper()
#     master_description = str(master.description) if hasattr(master, 'description') and master.description else ""

#     if requested_type == "DI" and master_name != "DIGITAL INPUT":
#         raise HTTPException(status_code=400, detail="module_type DI must be used with Digital Input module_id")
#     if requested_type == "DO" and master_name != "DIGITAL OUTPUT":
#         raise HTTPException(status_code=400, detail="module_type DO must be used with Digital Output module_id")

#     slots = await FRTUSlots.select(id=payload.slot_id, device_id=device_uuid)
#     if not slots:
#         raise HTTPException(status_code=400, detail="Given slot_id does not belong to this device")
#     slot = slots[0]
#     try:
#         slot_number = int(str(slot.name))
#     except Exception:
#         raise HTTPException(status_code=400, detail="Invalid slot name format in frtu_slots")

#     existing = await FRTUModules.select(slot_id=payload.slot_id)
#     if existing:
#         raise HTTPException(status_code=400, detail="Slot already occupied")

#     mtypes = await FRTUModuleType.select(name=requested_type)
#     if not mtypes:
#         raise HTTPException(status_code=400, detail="Invalid module_type")
#     mtype = mtypes[0]

#     info_key = "module_di_info" if requested_type == "DI" else "module_do_info"
#     general_info = payload.general_info or {}
#     general_info["slot_number"] = slot_number
#     general_info["slot_id"] = str(payload.slot_id)
#     general_info["module_name"] = "Digital Input" if requested_type == "DI" else "Digital Output"
#     general_info["module_type"] = requested_type

#     module_info = {
#         "general_info": general_info
#     }
    
#     full_attribute = {
#         "device_id": str(device_uuid),
#         "slot_number": slot_number,
#         info_key: module_info
#     }

#     try:
#         placed = await FRTUModules.insert(
#             slot_id=payload.slot_id,
#             name="Digital Input" if requested_type == "DI" else "Digital Output",
#             module_type=mtype.id,
#             description=master_description,
#             attribute=full_attribute,
#             channel=None,
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to save module: {e}")

#     try:
#         await asyncio.to_thread(
#             frtu_client.update_devids_conf,
#             slot_number,
#             requested_type,
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Module saved but failed to update devids.conf: {e}",
#         )

#     return {
#         "status": "success",
#         "http_code": 201,
#         "message": "DI/DO module added successfully with general_info",
#         "data": {
#             "module_id": str(placed.id),
#             "slot_id": str(placed.slot_id),
#             "module_type": requested_type,
#             "name": "Digital Input" if requested_type == "DI" else "Digital Output",
#             "general_info": general_info,
#         },
#     }

async def edit_di_module(
    device_id: str,
    device_type: str,
    payload: ConfigureDIModuleRequest,
    user_id: UUID,
):
    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    device = devices[0]
    db_type = (
        device.type.name
        if hasattr(device.type, "name")
        else (device.type.value if hasattr(device.type, "value") else str(device.type))
    )
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match for this device_id")

    requested_type = payload.module_type.strip().upper()
    if requested_type not in ("DI", "DO"):
        raise HTTPException(status_code=400, detail="Only DI/DO modules can be edited with this API")

    placed_list = await FRTUModules.select(id=payload.sub_module_id)
    if not placed_list:
        raise HTTPException(status_code=400, detail="Invalid module_id")
    placed = placed_list[0]
    placed_id = placed.id
    current_slot_id = placed.slot_id
    placed_name = placed.name

    slots_all: List[FRTUSlots] = await FRTUSlots.select(device_id=device_uuid)
    slot_by_id = {s.id: s for s in slots_all}

    def slot_no_for(slot_id: UUID) -> int:
        s = slot_by_id[slot_id]
        return int(str(s.name))

    if current_slot_id not in slot_by_id:
        raise HTTPException(status_code=400, detail="Current slot does not belong to this device")

    current_slot_no = slot_no_for(current_slot_id)

    target_slot_id: UUID = payload.slot_id if payload.slot_id is not None else current_slot_id
    if target_slot_id not in slot_by_id:
        raise HTTPException(status_code=400, detail="Given slot_id does not belong to this device")
    target_slot_no = slot_no_for(target_slot_id)

    mtype_rows = await FRTUModuleType.select(id=placed.module_type)
    if not mtype_rows:
        raise HTTPException(status_code=400, detail="Invalid module_type on module row")
    placed_type_name = mtype_rows[0].name.upper()
    if placed_type_name != requested_type:
        raise HTTPException(status_code=400, detail="module_type does not match placed module")

    user_slot_number = (payload.general_info or {}).get("slot_number")
    if user_slot_number is not None and int(user_slot_number) != target_slot_no:
        raise HTTPException(
            status_code=400,
            detail="slot_number in general_info does not match final slot",
        )

    user_card_type = (payload.general_info or {}).get("card_type")
    if user_card_type:
        ct_norm = str(user_card_type).strip().upper()
        if requested_type == "DI":
            if "DI-16" not in ct_norm or "DIGITAL INPUT" not in ct_norm:
                raise HTTPException(
                    status_code=400,
                    detail="card_type must be DI-16 Digital Input for DI module",
                )
        if requested_type == "DO":
            if "DO-10" not in ct_norm or "DIGITAL OUTPUT" not in ct_norm:
                raise HTTPException(
                    status_code=400,
                    detail="card_type must be DO-10 Digital Output for DO module",
                )

    new_slot_id = current_slot_id
    new_slot_no = current_slot_no
    partner_new_slot_no: int | None = None
    partner_type_name: str | None = None

    if target_slot_id != current_slot_id:
        modules_in_target = await FRTUModules.select(slot_id=target_slot_id)
        partner = next((m for m in modules_in_target if m.id != placed_id), None)

        if partner is None:
            new_slot_id = target_slot_id
            new_slot_no = target_slot_no
            placed_attr_move = dict(placed.attribute or {})
            placed_attr_move["slot_number"] = new_slot_no
            await FRTUModules.update(
                conditions={"id": placed_id},
                slot_id=new_slot_id,
                attribute=placed_attr_move,
            )
        else:
            partner_id = partner.id

            partner_attr = dict(partner.attribute or {})
            partner_attr["slot_number"] = current_slot_no
            await FRTUModules.update(
                conditions={"id": partner_id},
                slot_id=current_slot_id,
                attribute=partner_attr,
            )

            placed_attr_move = dict(placed.attribute or {})
            placed_attr_move["slot_number"] = target_slot_no
            await FRTUModules.update(
                conditions={"id": placed_id},
                slot_id=target_slot_id,
                attribute=placed_attr_move,
            )

            new_slot_id = target_slot_id
            new_slot_no = target_slot_no
            partner_new_slot_no = current_slot_no

            pt_rows = await FRTUModuleType.select(id=partner.module_type)
            partner_type_name = pt_rows[0].name.upper() if pt_rows else None

    placed = (await FRTUModules.select(id=placed_id))[0]
    final_attr: Dict[str, Any] = dict(placed.attribute or {})
    final_attr["slot_number"] = new_slot_no

    info_key = "module_di_info" if requested_type == "DI" else "module_do_info"
    existing_info = dict(final_attr.get(info_key) or {})
    general_info = dict(existing_info.get("general_info") or {})

    for k, v in (payload.general_info or {}).items():
        general_info[k] = v

    general_info["slot_number"] = new_slot_no
    general_info["slot_id"] = str(new_slot_id)
    general_info["module_name"] = placed_name
    general_info["module_type"] = requested_type
    if user_card_type:
        general_info["card_type"] = user_card_type

    existing_info["general_info"] = general_info
    final_attr[info_key] = existing_info

    await FRTUModules.update(
        conditions={"id": placed_id},
        slot_id=new_slot_id,
        attribute=final_attr,
    )

    try:
        await asyncio.to_thread(
            frtu_client.update_devids_conf,
            new_slot_no,
            requested_type,
        )
        if partner_new_slot_no is not None and partner_type_name:
            await asyncio.to_thread(
                frtu_client.update_devids_conf,
                partner_new_slot_no,
                partner_type_name,
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update devids.conf for DI/DO module: {e}",
        )

    return {
        "status": "success",
        "http_code": 200,
        "message": "DI/DO module updated successfully",
        "data": {
            "device_id": str(device_uuid),
            "slot_id": str(new_slot_id),
            "sub_module_id": str(placed_id),
            "module_type": requested_type,
            "slot_number": new_slot_no,
            "info_key": info_key,
            "info": existing_info,
        },
    }

async def get_di_module_detail(
    device_id: str,
    device_type: str,
    sub_module_id: str,
    user_id: UUID,
) -> Dict[str, Any]:
    try:
        device_uuid = UUID(device_id)
        sub_module_uuid = UUID(sub_module_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id or sub_module_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    device = devices[0]
    db_type = (
        device.type.name
        if hasattr(device.type, "name")
        else (device.type.value if hasattr(device.type, "value") else str(device.type))
    )
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match for this device_id")

    modules = await FRTUModules.select(id=sub_module_uuid)
    if not modules:
        raise HTTPException(status_code=404, detail="Module not found")
    module = modules[0]

    mtypes = await FRTUModuleType.select(id=module.module_type)
    if not mtypes:
        raise HTTPException(status_code=400, detail="Invalid module_type")
    module_type = mtypes[0].name.strip().upper()
    if module_type not in ("DI", "DO"):
        raise HTTPException(status_code=400, detail="Only DI/DO modules supported")

    slots = await FRTUSlots.select(id=module.slot_id)
    if not slots:
        raise HTTPException(status_code=400, detail="Module slot not found")
    slot = slots[0]

    attribute = dict(module.attribute or {})
    info_key = "module_di_info" if module_type == "DI" else "module_do_info"
    module_info = dict(attribute.get(info_key) or {})
    general_info = dict(module_info.get("general_info") or {})

    return {
        "status": "success",
        "http_code": 200,
        "message": f"{module_type} module details retrieved successfully",
        "device_id": str(device_uuid),
        "device_type": device_type,
        "sub_module_id": str(module.id),
        "module_type": module_type,
        "module_name": module.name,
        "slot_id": str(module.slot_id),
        "slot_no": int(str(slot.name)),
        "general_info": general_info
    }




