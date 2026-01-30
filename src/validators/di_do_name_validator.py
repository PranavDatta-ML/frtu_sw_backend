from uuid import UUID

from fastapi import HTTPException
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules


async def validate_unique_module_name(
    device_id: UUID,
    module_type_name: str,
    module_name: str,
    exclude_module_id: UUID | None = None,
):
    if not module_name:
        return

    module_types = await FRTUModuleType.select(name=module_type_name.upper())
    if not module_types:
        return

    module_type_id = module_types[0].id
    modules = await FRTUModules.select(module_type=module_type_id)

    for module in modules:
        if exclude_module_id and module.id == exclude_module_id:
            continue

        attr = module.attribute or {}
        if attr.get("device_id") != str(device_id):
            continue

        info_key = f"module_{module_type_name.lower()}_info"
        existing_name = (
            attr.get(info_key, {})
            .get("general_info", {})
            .get("name")
        )

        if existing_name and existing_name.strip().lower() == module_name.strip().lower():
            raise HTTPException(
                400,
                f"{module_type_name} module name '{module_name}' already exists for this device",
            )
