from src.routers.base import router as BaseRouter
from src.routers.tasks import router as TaskRouter
from src.routers.frtu_users import router as FRTUUserRouter
from src.routers.frtu_platform_admins import router as FRTUPlatformAdminRouter
from src.routers.frtu_tenants import router as FRTUTenantRouter
from src.routers.frtu_projects import router as FRTUProjectRouter
from src.routers.frtu_sites import router as FRTUSiteRouter
from src.routers.frtu_devices import router as FRTUDeviceRouter
from src.routers.frtu_slots import router as FRTUSlotRouter
from src.routers.frtu_modules import router as FRTUModuleRouter


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
    app.include_router(FRTUUserRouter, prefix='')
    app.include_router(FRTUPlatformAdminRouter, prefix='')
    app.include_router(FRTUTenantRouter, prefix='')
    app.include_router(FRTUProjectRouter, prefix='')
    app.include_router(FRTUSiteRouter, prefix='')
    app.include_router(FRTUDeviceRouter, prefix='')
    app.include_router(FRTUSlotRouter, prefix='')
    app.include_router(FRTUModuleRouter, prefix='')

    app.include_router(TaskRouter, prefix='/api/v1')  # Tasks route registration
    