import anyjson
import functools
import logging
import netifaces
import pickle
import threading
import urllib
from celery.result import AsyncResult
from celery import current_app
from tornado.web import RequestHandler, URLSpec, HTTPError
from tornado import gen
from tornado.ioloop import IOLoop
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
            raise HTTPError(400, "task_id is missing")
        if task_id not in self._table.callbacks:
            raise HTTPError(400, "invalid task_id argument")
        retval = self.get_argument('retval', None)
        if retval is None:
            raise HTTPError(400, "retval argument is missing")
        else:
            try:
                retval = pickle.loads(urllib.unquote(retval))
            except Exception:
                logger.exception("failed to parse retval argument")
                raise HTTPError(400)
        state = self.get_argument('state', None)
        if state is None:
            raise HTTPError(400, "state argument is missing")
        IOLoop.instance().add_callback(self._table.callbacks[task_id], TaskResult(state, retval))
        del self._table.callbacks[task_id]
        self.set_header('Content-Type', 'application/json')
        self.finish(anyjson.dumps({"status": "success", "retval": None}))


class TaskException (Exception):
    pass


class TaskFailure (TaskException):

    def __init__(self, task_result):
        super(TaskFailure, self).__init__()
        self.error = task_result.error
        self.task_result = task_result


class TaskTimeout (TaskException):
    pass


class TaskResult (object):

    def __init__(self, state, result):
        self.state = state
        if isinstance(result, Exception):
            self.error = result
            self.result = None
        else:
            self.result = result
            self.error = None


class AsyncTask (gen.Task):

    # noinspection PyMissingConstructor
    def __init__(self, task, args=None, kwargs=None, timeout=None, **options):
        assert "callback" not in options
        kwargs = kwargs_insert_torcel_hooks(kwargs)
        try:
            self.func = task.apply_async
        except KeyError:
            self.func = functools.partial(current_app.send_task, task)
        self.args = [args, kwargs]
        self.kwargs = options
        self.timeout = timeout

    def get_result(self):
        result = self.runner.pop_result(self.key)
        if result.state == 'TIMEOUT':
            raise TaskTimeout()
        elif result.state != 'SUCCESS':
            raise TaskFailure(result)
        return result.result

    def start(self, runner):
        self.runner = runner
        self.key = object()
        runner.register_callback(self.key)
        callback = runner.result_callback(self.key)
        task_id = self.func(*self.args, **self.kwargs)
        ResultCallback(task_id, callback, self.timeout)

ApplyAsyncTask = AsyncTask  # just an alias


class ResultCallback (object):

    def __init__(self, task_id, callback, timeout=None):
        if isinstance(task_id, AsyncResult):
            task_id = task_id.id
        self.task_id = task_id
        self.callback = callback
        self.timeout = timeout
        self.finished = False
        DispatchResultHandler.add_callback(self)
        if self.timeout is not None:
            self.timeout_handler = IOLoop.instance().add_timeout(
                IOLoop.instance().time() + self.timeout, self.on_timeout)

    def __call__(self, task_result):
        if self.finished:
            return
        self.callback(task_result)
        self.finished = True
        if self.timeout is not None:
            IOLoop.instance().remove_timeout(self.timeout_handler)

    def on_timeout(self):
        # TODO: revoke the task from broker?
        # TODO: remove record from DispatchResultHandler?
        self.finished = True
        self.callback(TaskResult('TIMEOUT', None))


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