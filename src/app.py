from fastapi import FastAPI

from src import Settings
from src.routers import include_router
# from src.middleware im

# Load settings (cached using get_settings)
settings = Settings.get_settings()

# Initialize FastAPI app with project name and version from settings
app = FastAPI(
    title=settings.PROJECT_NAME, 
    version=settings.PROJECT_VERSION
)

# app.add_middleware(
#     JWTAuthMiddleware,
#     secret_key=settings.JWT_SECRET_KEY,
#     algorithm=settings.JWT_ALGORITHM,
#     exclude_paths={"/docs", "/redoc", "/openapi.json", "/health", "/auth/login"},
#     audience=settings.JWT_AUDIENCE,
#     issuer=settings.JWT_ISSUER,
# )

include_router(app)