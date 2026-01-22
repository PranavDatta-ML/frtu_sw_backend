from uuid import UUID

from src.models.frtu_user_assignment import FRTUUserAssignment


async def is_child_of(requester_id: UUID, target_user_id: UUID) -> bool:
    rows = await FRTUUserAssignment.select(
        user_id=target_user_id,
        admin_id=requester_id,
    )
    return bool(rows)