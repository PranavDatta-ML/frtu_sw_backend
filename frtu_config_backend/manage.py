#!/usr/bin/env python

from src import log
from src.app import app
from src import Settings
from src.core.db.session import DatabaseSession
from src.services.redis_service import test_redis_connection

settings = Settings()
@app.on_event('startup')
async def app_startup():
    """
    Called when the application starts.
    Logs the startup event.
    """
    #await DatabaseSession.create_all()
    log.info('Starting Application...')
    

@app.on_event('shutdown')
async def app_shutdown():
    """
    Called when the application stops.
    Logs the shutdown event.
    """
    log.info('Stopping Application, please wait...')

@app.on_event('startup')
async def app_startup():
    try:
        healthy = await test_redis_connection()
        log.info(f'Starting FRTU Application - Redis...')
        print(f"Redis Connected Successfully: {'healthy' if healthy else 'failed'}")
    except Exception as e:
        log.error(f'App startup failed: {e}')
        raise

@app.on_event('shutdown')
async def app_shutdown():
    log.info('Stopping FRTU Application...')

@app.get("/health")
async def health():
    healthy = await test_redis_connection()
    return {
        "status": "healthy" if healthy else "unhealthy",
        "redis": healthy,
        "environment": settings.get_environment()
    }