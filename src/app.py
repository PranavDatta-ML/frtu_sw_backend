from fastapi import FastAPI

from src import Settings
from src.routers import include_router


# Load settings (cached using get_settings)
settings = Settings.get_settings()


# Initialize FastAPI app with project name and version from settings
app = FastAPI(
    title=settings.PROJECT_NAME, 
    version=settings.PROJECT_VERSION
)

include_router(app)