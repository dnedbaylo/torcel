import anyjson
import functools
import netifaces
import threading
import urllib
from tornado.web import RequestHandler, URLSpec, HTTPError
from tornado.options import options


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
            retval = anyjson.loads(urllib.unquote(retval))
        self._table.callbacks[task_id](retval)
        del self._table.callbacks[task_id]
        self.set_header('Content-Type', 'application/json')
        self.finish(anyjson.dumps({"status": "success", "retval": None}))


class ResultCallback (object):

    def __init__(self, task_id, callback):
        self.task_id = task_id
        self.callback = callback
        DispatchResultHandler.add_callback(self)

    def __call__(self, result):
        self.callback(result)


class CeleryMixin (object):
    _celery_webhook_url = None

    @classmethod
    def get_celery_webhook_url(cls):
        """
        Should return IP address of current machine.
        Overwrite it if needed
        """
        if cls._celery_webhook_url is not None:
            return cls._celery_webhook_url
        try:
            iface = (x for x in netifaces.interfaces() if x != 'lo').next()
        except StopIteration:
            import warnings
            warnings.warn("cannot find network interface other than `lo`, using 127.0.0.1 as instance ip address")
            cls._celery_webhook_url = '127.0.0.1'
        else:
            cls._celery_webhook_url = netifaces.ifaddresses(iface)[2][0]['addr']
        cls._celery_webhook_url = "http://%s:%s/celery-dispatch-result" % (cls._celery_webhook_url, options.port)
        return cls._celery_webhook_url

    def get_result(self, task_id):
        return functools.partial(ResultCallback, task_id)

    @property
    def task_kwargs(self):
        return {"_torcel": True, "_torcel_callback_url": self.get_celery_webhook_url()}


urlspec = [
    URLSpec('/celery-dispatch-result', DispatchResultHandler),
]