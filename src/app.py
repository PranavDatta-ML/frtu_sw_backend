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
    version=settings.PROJECT_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

include_router(app)
