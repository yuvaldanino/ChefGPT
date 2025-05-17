from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def test_celery_task():
    """
    A simple test task to verify Celery is working properly.
    """
    logger.info("Test Celery task is running!")
    return "Celery is working!" 