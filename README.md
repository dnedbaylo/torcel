About
======

torcel - Celery and Tornado integration that allows to call celery tasks in non-blocking, asynchronous aproach.
The way it does it is via simple HTTP callback that is called from celery signal task_postrun. No IOLoop timeouts,
no UNIX sockets, no custom broker connections and custom TaskProducer. Plain simple HTTP callback.


Usage
=====

Calling Celery tasks from Tornado RequestHandler:

    from tornado import gen, web
    from torcel import AsyncTask, TaskFailed
    from . import tasks

    class AsyncHandler(web.RequestHandler):

        @asynchronous
        @gen.coroutine
        def get(self):
            try:
                result = yield AsyncTask(tasks.echo, args=['Hello world!'])
            except TaskFailed, e:
                self.finish("task failed with exception: %s" % repr(e.error))
            else:
                self.finish("task succeeded with result: %s" % repr(result))

