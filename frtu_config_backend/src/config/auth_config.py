from src.core.settings import Settings

_settings = Settings.get_settings()

SECRET_KEY = _settings.JWT_SECRET_KEY
ALGORITHM = _settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = _settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES