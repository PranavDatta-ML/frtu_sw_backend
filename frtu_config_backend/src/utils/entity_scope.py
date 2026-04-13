from uuid import UUID
from typing import Optional, List

from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_roles import FRTURoles
from src.models.frtu_entities import FRTUEntities
from src import log

ROLE_LEVEL = {
    "SUPER_ADMIN": 100,
    "PLATFORM_ADMIN": 90,
    "TENANT_ADMIN": 80,
    "PROJECT_ADMIN": 70,
    "SITE_ADMIN": 60,
    "USER": 10
}
async def get_user_role_level(user_id: UUID) -> int:
    assignments = await FRTUUserAssignment.select(user_id=user_id)

    if not assignments:
        return 0
    role_id = assignments[0].role_id

    role = await FRTURoles.select(id=role_id)
    if not role:
        return 0

    role_name = role[0].name.strip().upper()

    return ROLE_LEVEL.get(role_name, 0)


async def user_can_access_entity(user_id: UUID, target_entity_id: UUID) -> bool:
    user_level = await get_user_role_level(user_id)

    if user_level == ROLE_LEVEL["SUPER_ADMIN"]:
        return True

    entities = await FRTUEntities.select(entity_id=target_entity_id)
    if not entities:
        log.info(f"[Hierarchy] Target entity not found: {target_entity_id}")
        return False

    target = entities[0]
    current_creator = target.created_by

    while current_creator:
        if current_creator == user_id:
            return True

        parent_entity = await FRTUEntities.select(entity_id=current_creator)
        if not parent_entity:
            break

        current_creator = parent_entity[0].created_by

    log.info(f"[Hierarchy] User {user_id} NOT permitted to access entity {target_entity_id}")
    return False
