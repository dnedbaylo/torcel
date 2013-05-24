from celery import Celery, current_task
from celery.utils.log import get_task_logger
from random import randint
from time import sleep
from torcel import signals

celery = Celery('tasks', broker='amqp://guest@localhost//')
task_logger = get_task_logger(__name__)


@celery.task
def task1():
    task_logger.info("id: %s", current_task.request.id)
    s = randint(1, 5)
    sleep(s)
    return {"success": True, "wait": s}