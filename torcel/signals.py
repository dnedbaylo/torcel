from celery.signals import task_postrun
from celery.task.http import HttpDispatch
import anyjson

@task_postrun.connect
def tornado_notify(args=None, kwargs=None, task_id=None, task=None, retval=None, state=None, signal=None, sender=None):
    if '_torcel' not in kwargs:
        return
    callback_url = kwargs.get('_torcel_callback_url', None)
    if callback_url is None:
        return
    d = HttpDispatch(task_kwargs={"success": True, "task_id": task_id, "retval": anyjson.dumps(retval)},
                     url=callback_url, method="POST")
    d.dispatch()
