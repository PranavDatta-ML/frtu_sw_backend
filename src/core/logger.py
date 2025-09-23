import logging
from src.core.settings import Settings

# Initialize settings
settings = Settings.get_settings()

# Configure logging with format and log level from settings
logging.basicConfig(
    format="[%(asctime)s]: %(message)s", 
    level=getattr(logging, settings.LOG_LEVEL)
)

# Create logger instance for the application
log = logging.getLogger('app')

# Initialize attributes for logging context
attrs = {
    'request_id': '',
    'endpoint': ''
}
