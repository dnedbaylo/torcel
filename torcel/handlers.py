import anyjson
import functools
import logging
import netifaces
import threading
import urllib
from celery.result import AsyncResult
from tornado.web import RequestHandler, URLSpec, HTTPError
from tornado.options import options

_celery_webhook_url = None
logger = logging.getLogger("torcel.handlers")


class DispatchResultHandler (RequestHandler):
    _table = threading.local()
    _table.callbacks = {}

    @classmethod
    def add_callback(cls, callback):
        cls._table.callbacks[callback.task_id] = callback

    def post(self):
        task_id = self.get_argument('task_id', None)
        if task_id is None:
            raise HTTPError(400)
        if task_id not in self._table.callbacks:
            raise HTTPError(400)
        retval = self.get_argument('retval', None)
        if retval is not None:
            try:
                retval = anyjson.loads(urllib.unquote(retval))
            except Exception:
                logger.exception("failed to parse retval argument")
                raise HTTPError(400)
        self._table.callbacks[task_id](retval)
        del self._table.callbacks[task_id]
        self.set_header('Content-Type', 'application/json')
        self.finish(anyjson.dumps({"status": "success", "retval": None}))


class ResultCallback (object):

    def __init__(self, task_id, callback):
        if isinstance(task_id, AsyncResult):
            task_id = task_id.id
        self.task_id = task_id
        self.callback = callback
        DispatchResultHandler.add_callback(self)

    def __call__(self, result):
        self.callback(result)


def get_celery_webhook_url():
    """
    Should return IP address of current machine.
    Overwrite it if needed
    """
    global _celery_webhook_url
    if _celery_webhook_url is not None:
        return _celery_webhook_url
    try:
        iface = (x for x in netifaces.interfaces() if x != 'lo').next()
    except StopIteration:
        import warnings
        warnings.warn("cannot find network interface other than `lo`, using 127.0.0.1 as instance ip address")
        _celery_webhook_url = '127.0.0.1'
    else:
        _celery_webhook_url = netifaces.ifaddresses(iface)[2][0]['addr']
    _celery_webhook_url = "http://%s:%s/celery-dispatch-result" % (_celery_webhook_url, options.port)
    return _celery_webhook_url


def kwargs_insert_torcel_hooks(kwargs):
    kwargs = kwargs or {}
    kwargs["_torcel_callback_url"] = get_celery_webhook_url()
    return kwargs


class CeleryHandlerMixin (object):

    def get_task_result(self, task_id, callback=None):
        if callback is None:
            return functools.partial(ResultCallback, task_id)
        else:
            return ResultCallback(task_id, callback)

    def apply_async(self, task, args=None, kwargs=None, **options):
        kwargs = kwargs_insert_torcel_hooks(kwargs)
        return task.apply_async(args, kwargs, **options)


urlspec = [
    URLSpec('/celery-dispatch-result', DispatchResultHandler),
]