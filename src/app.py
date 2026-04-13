from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import Settings
from src.routers import include_router

# from src.middleware im

# Load settings (cached using get_settings)
settings = Settings.get_settings()

# Initialize FastAPI app with project name and version from settings
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    redirect_slashes=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=settings.CORS_ALLOWED_METHODS.split(","),
    allow_headers=settings.CORS_ALLOWED_HEADERS.split(","),
)

include_router(app)
