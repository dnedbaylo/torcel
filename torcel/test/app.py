import torcel.handlers
import torcel.producer
import tornado.ioloop
from tornado import gen, httpserver
from tornado.options import options, define
from tornado.web import Application, RequestHandler, URLSpec, asynchronous
import tasks

torcel.producer.setup_producer()


class Example1RequestHandler(RequestHandler, torcel.handlers.CeleryHandlerMixin):

    @asynchronous
    @gen.engine
    def get(self):
        task_id = self.apply_async(tasks.task1).id
        result = yield gen.Task(self.get_task_result(task_id))
        self.finish("result: %s" % result)


class Example2RequestHandler(RequestHandler, torcel.handlers.CeleryHandlerMixin):

    @asynchronous
    @gen.engine
    def get(self):
        result = yield gen.Task(self.get_task_result, self.apply_async(tasks.task1).id)
        self.finish("result: %s" % result)


class Example3RequestHandler(RequestHandler, torcel.handlers.CeleryHandlerMixin):

    @asynchronous
    @gen.engine
    def get(self):
        result = yield gen.Task(self.get_task_result, self.apply_async(tasks.task1))
        self.finish("result: %s" % result)


class Example4RequestHandler(RequestHandler, torcel.handlers.CeleryHandlerMixin):

    @asynchronous
    @gen.engine
    def get(self):
        result = yield gen.Task(tasks.task1.apply_async)
        self.finish("result: %s" % result)


urlspec = [
    URLSpec('/example1', Example1RequestHandler),
    URLSpec('/example2', Example2RequestHandler),
    URLSpec('/example3', Example3RequestHandler),
    URLSpec('/example4', Example4RequestHandler),
]
urlspec.extend(torcel.handlers.urlspec)


def get_app():
    return Application(urlspec, debug=True)


if __name__ == '__main__':
    define("port", default=8080, type=int, help="run on the given port")
    http_server = httpserver.HTTPServer(get_app())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
