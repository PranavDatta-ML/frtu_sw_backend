from src.utils.version import get_version_data
from src import HttpStatusCode
from src import log
from src import Settings


async def version_view(settings: Settings):
    """
    Returns the version of the application.

    Args:
        settings: Dependency injection for application settings.

    Returns:
        A dictionary containing the version information.
    """

    version_data = await get_version_data(settings)
    log.info("Handling version route")
    return HttpStatusCode.OK.response(data=version_data)