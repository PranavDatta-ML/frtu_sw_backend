# from sqlalchemy.orm import relationship
from src.models.frtu_roles import FRTURoles
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_user_assignment import FRTUUserAssignment
__all__ = [
    "FRTURoles",
    "FRTUPermissions",
    "FRTURolePermissions",
    "FRTUUserAssignment",
]