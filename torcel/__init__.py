from . handlers import AsyncTask, TaskFailed

def setup_goodies():
    from torcel import producer
    producer.setup_producer()