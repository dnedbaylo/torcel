import logging
import pickle
import threading
from celery.signals import task_postrun, task_prerun
from celery.task.http import HttpDispatch

local = threading.local()
local.callback_url = {}
logger = logging.getLogger("torcel.signals")


@task_prerun.connect
def tornado_prerun(task_id, kwargs, **_kwargs):
    callback_url = kwargs.pop('_torcel_callback_url', None)
    if callback_url is not None:
        local.callback_url[task_id] = callback_url


@task_postrun.connect
def tornado_postrun(task_id, retval=None, state=None, **kwargs):
    if task_id not in local.callback_url:
        return
    callback_url = local.callback_url.pop(task_id)
    d = HttpDispatch(task_kwargs={"state": state, "task_id": task_id, "retval": pickle.dumps(retval)},
                     url=callback_url, method="POST")
    try:
        d.dispatch()
    except Exception:
        logger.exception("failed to dispatch tornado callback: %s", callback_url)
