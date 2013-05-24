import torcel.handlers
import torcel.producer
import tornado.ioloop
from tornado import gen, httpserver
from tornado.web import Application, RequestHandler, URLSpec, asynchronous
from torcel import TaskFailure, TaskTimeout, AsyncTask
import tasks


class Task1RequestHandler(RequestHandler):
    """
    Uses AsyncTask yield point
    """
    @asynchronous
    @gen.coroutine
    def get(self):
        try:
            result = yield AsyncTask(tasks.task1)
        except TaskFailure, e:
            self.finish("task failed: state: %s, exception: %s" % (e.task_result.state, repr(e.error)))
        else:
            self.finish("result: %s" % result)


class TaskFailRequestHandler(RequestHandler):
    """
    Uses AsyncTask yield point
    """
    @asynchronous
    @gen.coroutine
    def get(self):
        try:
            result = yield AsyncTask(tasks.task_fails)
        except TaskFailure, e:
            self.finish("task failed: state: %s, exception: %s" % (e.task_result.state, repr(e.error)))
        else:
            self.finish("result: %s" % result)


class TaskTimeoutRequestHandler(RequestHandler):
    """
    Uses AsyncTask yield point
    """
    @asynchronous
    @gen.coroutine
    def get(self):
        try:
            result = yield AsyncTask(tasks.task_timeout, timeout=5)
        except TaskTimeout:
            self.finish("task timed out")
        else:
            self.finish("result: %s" % result)


urlspec = [
    URLSpec('/task1', Task1RequestHandler),
    URLSpec('/task_fail', TaskFailRequestHandler),
    URLSpec('/task_timeout', TaskTimeoutRequestHandler),
]
urlspec.extend(torcel.handlers.urlspec)


def get_app():
    return Application(urlspec, debug=True)


if __name__ == '__main__':
    from tornado.options import options, define
    define("port", default=8080, type=bool, help="run on the given port")
    http_server = httpserver.HTTPServer(get_app())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
