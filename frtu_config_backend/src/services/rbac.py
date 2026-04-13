from uuid import UUID
from src.middleware.rbac import ChildScopeError, SelfEditError
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_roles import FRTURoles
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_users import FRTUUsers


class RBACService:
    def __init__(self, actor_id: UUID):
        self.actor_id = actor_id

    async def _is_child(self, owner_id: UUID) -> bool:
        owner = (await FRTUUsers.select(id=owner_id))[0]
        return owner.attribute.get("created_by") == str(self.actor_id)

    def _block_self(self, owner_id: UUID):
        if owner_id == self.actor_id:
            raise SelfEditError()

    async def can_manage_role(self, role: FRTURoles):
        self._block_self(role.user_id)
        if not await self._is_child(role.user_id):
            raise ChildScopeError()

    async def can_manage_permission(self, perm: FRTUPermissions):
        self._block_self(perm.user_id)
        if not await self._is_child(perm.user_id):
            raise ChildScopeError()

    async def has_permission(self, action: str, resource: str) -> bool:
        assigns = await FRTUUserAssignment.select(user_id=self.actor_id)
        for a in assigns:
            role_perms = await FRTURolePermissions.select(role_id=a.role_id)
            for rp in role_perms:
                perm = (await FRTUPermissions.select(id=rp.permission_id))[0]
                for rule in perm.attribute:
                    if rule["resource"] == resource and action in rule["action"]:
                        return True
        return False