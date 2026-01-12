from src.routers.base import router as BaseRouter
from src.routers.tasks import router as TaskRouter
from src.routers.auth import router as TenantRouter
from src.routers.frtu_users import router as FRTUUserRouter
from src.routers.frtu_roles import router as FRTURolesRouter
from src.routers.frtu_permissions import router as FRTUPermissionsRouter
from src.routers.frtu_role_permissions import router as FRTURolePermissionsRouter
from src.routers.frtu_user_assignment import router as FRTUUserAssinmentRouter
from src.routers.frtu_platform_admins import router as FRTUPlatformAdminRouter
from src.routers.frtu_tenants import router as FRTUTenantRouter
from src.routers.frtu_projects import router as FRTUProjectRouter
from src.routers.frtu_sites import router as FRTUSiteRouter
from src.routers.frtu_devices import router as FRTUDeviceRouter
from src.routers.frtu_slots import router as FRTUSlotRouter
from src.routers.frtu_modules import router as FRTUModuleRouter
from src.routers.frtu_di_module_info import router as FRTUDIModuleInfoRouter
from src.routers.frtu_do_module_info import router as FRTUDOModuleInfoRouter
from src.routers.frtu_modbus_rtu import router as FRTUModbusRTUInfoRouter
from src.routers.frtu_module_master import router as FRTUModuleMasterRouter
from src.routers.frtu_auto_discover_module import router as FRTUModulesAutoDiscoverRouter
from src.routers.frtu_modules_slot_detail import router as FRTUModulesSlotDetailRouter
from src.routers.frtu_manual_module import router as FRTUManualModuleRouter
from src.routers.frtu_di_module import router as FRTUChannelDIConfigureRouter
from src.routers.frtu_di_module_channel import router as FRTUDIChannelConfigureRouter
from src.routers.frtu_protocols import router as FRTUProtocolRouter


def include_router(app):
    """
    Registers all the necessary routers with the FastAPI application instance.

    Args:
        app: The FastAPI application instance to which the routers will be added.

    This function registers the following routers:
    - BaseRouter: Handles base routes.
    - TaskRouter: Handles task-related routes.
    """
    app.include_router(BaseRouter, prefix='/api') 
    app.include_router(TenantRouter, prefix='')
    app.include_router(FRTUUserRouter, prefix='')
    app.include_router(FRTURolesRouter, prefix='')
    app.include_router(FRTUPermissionsRouter, prefix='')
    app.include_router(FRTURolePermissionsRouter, prefix='')
    app.include_router(FRTUUserAssinmentRouter, prefix='')
    app.include_router(FRTUPlatformAdminRouter, prefix='')
    app.include_router(FRTUTenantRouter, prefix='')
    app.include_router(FRTUProjectRouter, prefix='')
    app.include_router(FRTUSiteRouter, prefix='')
    app.include_router(FRTUDeviceRouter, prefix='')
    app.include_router(FRTUSlotRouter, prefix='')
    app.include_router(FRTUModuleRouter, prefix='')
    app.include_router(FRTUDIModuleInfoRouter, prefix='')
    app.include_router(FRTUDOModuleInfoRouter, prefix='')
    app.include_router(FRTUModbusRTUInfoRouter, prefix='')
    app.include_router(FRTUModuleMasterRouter, prefix='')
    app.include_router(FRTUModulesAutoDiscoverRouter, prefix='')
    app.include_router(FRTUModulesSlotDetailRouter, prefix='')
    app.include_router(FRTUManualModuleRouter, prefix='')
    app.include_router(FRTUChannelDIConfigureRouter, prefix='')
    app.include_router(FRTUDIChannelConfigureRouter, prefix='')
    app.include_router(FRTUProtocolRouter, prefix='')

    app.include_router(TaskRouter, prefix='/api/v1')  # Tasks route registration
    