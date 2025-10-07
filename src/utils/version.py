import traceback

from src import log
from src import Settings
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio


async def check_database_status(bind_key: str, conn_str: str) -> dict:
    """
    Check the connectivity status of a database.

    Args:
        bind_key: The key for the database bind.
        conn_str: The connection string for the database.

    Returns:
        A dictionary containing the bind key and its connectivity status.
    """
    engine = create_async_engine(conn_str)

    try:
        async with engine.begin() as conn:
            try:
                await conn.execute(text("SELECT 1"))  # Simple query to check connectivity
                return {bind_key: 'UP'}
            except SQLAlchemyError:
                return {bind_key: 'DOWN'}
            finally:
                await engine.dispose()  # Close the engine connection
    except Exception as e:
        log.error(traceback.format_exc())
        return {bind_key: 'DOWN'}


async def get_version_data(settings: Settings) -> dict:
    """
    Creates the version data dictionary including database connectivity status.

    Args:
        settings: The application settings instance.

    Returns:
        A dictionary containing version details and connectivity status of the application.
    """
    version_data = {
        'name': settings.PROJECT_NAME,
        'version': settings.PROJECT_RELEASE,
        'environment': settings.get_environment(),
        'status': 'UP',
        'databases': {}
    }

    # Check status for each database
    tasks = []
    for bind_key, conn_str in settings.DATABASE_BINDS.items():
        tasks.append(check_database_status(bind_key, conn_str))

    db_status_results = await asyncio.gather(*tasks)

    # Combine the results into the databases dictionary
    for db_status in db_status_results:
        version_data['databases'].update(db_status)

    return version_data
