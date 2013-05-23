import torcel.handlers
import tornado.ioloop
from tornado import gen, httpserver
from tornado.options import options, define
from tornado.web import Application, RequestHandler, URLSpec, asynchronous
import tasks


class Task1RequestHandler (RequestHandler, torcel.handlers.CeleryMixin):

    @asynchronous
    @gen.engine
    def get(self):
        task_id = tasks.task1.apply_async(kwargs=self.task_kwargs).id
        result = yield gen.Task(self.get_result(task_id))
        self.finish("result: %s" % result)


urlspec = [
    URLSpec('/task1', Task1RequestHandler),
]
urlspec.extend(torcel.handlers.urlspec)


def get_app():
    return Application(urlspec, debug=True)


if __name__ == '__main__':
    define("port", default=8080, type=int, help="run on the given port")
    http_server = httpserver.HTTPServer(get_app())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
