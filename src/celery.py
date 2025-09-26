import asyncio
from celery import Celery
from kombu import Exchange, Queue

from src import log
from src import Settings


# Load settings (cached using get_settings)
settings = Settings.get_settings()


# Initialize Celery app
app = Celery()
app.config_from_object(settings, namespace='CELERY')

# Dynamically initialize queue settings
QUEUES = [Queue(queue_name, Exchange(queue_name), routing_key=queue_name) for queue_name in settings.CELERY_QUEUE_NAMES.split(',')]
app.conf.task_queues = QUEUES
app.conf.task_serializer = 'pickle'
app.conf.accept_content = ['pickle']


@app.task(name='handle_scheduled_task')
def handle_task(handler_instance, scheduled_task_master_data, scheduled_task_config_data, interval_data):
    log.info(f'Getting event loop in `handle_scheduled_task`')
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        log.info(f'Creating event loop in `handle_scheduled_task`')
        loop = asyncio.new_event_loop()

    try:
        return loop.run_until_complete(handler_instance.handle_task(scheduled_task_master_data, scheduled_task_config_data, interval_data))
    except Exception as e:
        log.info(f'Failed to run coroutine error={e}')
    # finally:
    #     loop.close()