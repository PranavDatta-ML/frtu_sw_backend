#!/usr/bin/env python

from src import log
from src.app import app
from src.core.db.session import DatabaseSession


@app.on_event('startup')
async def app_startup():
    """
    Called when the application starts.
    Logs the startup event.
    """
    await DatabaseSession.create_all()
    log.info('Starting Application...')
    

@app.on_event('shutdown')
async def app_shutdown():
    """
    Called when the application stops.
    Logs the shutdown event.
    """
    log.info('Stopping Application, please wait...')
