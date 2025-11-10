from functools import lru_cache
from typing import Dict

from pydantic_settings import BaseSettings
from pydantic import Field
from pydantic import validator


class Settings(BaseSettings):
    """
    Pydantic configuration settings for the application.
    """
    PROJECT_NAME: str = "FRTU BACKEND SERVICE"
    PROJECT_RELEASE: str = "DAY=20250923.RELEASE=1"
    PROJECT_VERSION: str = Field(default="0.0.0", env="PROJECT_VERSION")

    DEBUG: int = Field(default=1, env="DEBUG")
    LOG_LEVEL: str = Field(default='INFO')

    ALLOWED_HOOK_PROTOCOLS: str = Field(default='http,ftp,smtp', env="ALLOWED_HOOK_PROTOCOLS")

    # CORS settings
    CORS_ALLOWED_ORIGINS: str = Field(default="*", env="CORS_ALLOWED_ORIGINS")
    CORS_ALLOWED_METHODS: str = Field(default="*", env="CORS_ALLOWED_METHODS")
    CORS_ALLOWED_HEADERS: str = Field(default="*", env="CORS_ALLOWED_HEADERS")

    # Celery configuration
    CELERY_BROKER_URL: str = Field(default="amqp://guest:guest@127.0.0.1:5672", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="db+postgresql://postgres:postgres@127.0.0.1:5432/postgres",
                                       env="CELERY_RESULT_BACKEND")
    CELERY_RESULT_EXPIRES: int = Field(default=86400, env="CELERY_RESULT_EXPIRES")
    CELERY_QUEUE_NAMES: str = Field(default='http', env="ALLOWED_HOOK_PROTOCOLS")

    # Database binds
    DATABASE_URI: str = Field(
        default="postgresql+asyncpg://postgres:***REMOVED-DB-PASSWORD-2***@172.29.3.30:55432/frtu_conf_db",
        env="DATABASE_URI")

    JWT_SECRET_KEY: str = Field(default="***REMOVED-JWT-SECRET-2***", env="JWT_SECRET")

    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="JWT_ALGORITHM")
    JWT_AUDIENCE: str = Field(default="www.etlab.co", env="frtu")
    JWT_ISSUER: str = Field(default="www.etlab.co", env="frtu")

    DATABASE_BINDS: Dict[str, str] = {}

    def __init__(self, **values):
        super().__init__(**values)
        self.DATABASE_BINDS = {
            'public': self.DATABASE_URI,
        }

    @validator("DEBUG", pre=True, always=True)
    def strip_env_values(cls, value: str) -> str:
        """
        Removes whitespace from environment variable values.

        :param value: The value of the environment variable.
        :return: Stripped value if it's a string.
        """
        return value.strip() if isinstance(value, str) else value

    def get_environment(self) -> str:
        """
        Determines the environment based on the settings.

        Args:
            settings: The application settings instance.

        Returns:
            A string indicating the current environment ("DEVELOPMENT" or "PRODUCTION").
        """
        return "DEVELOPMENT" if int(self.DEBUG) else "PRODUCTION"

    @classmethod
    @lru_cache()
    def get_settings(cls) -> "Settings":
        """
        Returns the singleton instance of the Settings class using lru_cache for caching.
        """
        return cls()
