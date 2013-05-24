from celery.app.amqp import TaskProducer, AMQP
from torcel.handlers import ResultCallback, kwargs_insert_torcel_hooks


class TorcelTaskProducer (TaskProducer):

    def publish_task(self, task_name, task_args=None, task_kwargs=None, *args, **kwargs):
        callback = kwargs.pop('callback', None)
        if callback is not None and not callable(callback):
            raise ValueError("callback should be callable")
        if callback is not None:
            task_kwargs = kwargs_insert_torcel_hooks(task_kwargs)
        task_id = super(TorcelTaskProducer, self).publish_task(task_name, task_args, task_kwargs, *args, **kwargs)
        if callback is not None:
            ResultCallback(task_id, callback)
        return task_id


def setup_producer():
    AMQP.producer_cls = TorcelTaskProducer