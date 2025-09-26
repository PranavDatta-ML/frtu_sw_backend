from src.routers.base import router as BaseRouter
from src.routers.tasks import router as TaskRouter
from src.routers.frtu_devices import router as FRTUDeviceRouter
from src.routers.frtu_platform_admins import router as FRTUPlatformAdminRouter
from src.routers.auth import router as AuthRouter


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
    app.include_router(FRTUDeviceRouter, prefix='/api/frtu')
    app.include_router(FRTUPlatformAdminRouter, prefix='/api/admin')
    app.include_router(AuthRouter, prefix='/api/auth')

    app.include_router(TaskRouter, prefix='/api/v1')  # Tasks route registration
