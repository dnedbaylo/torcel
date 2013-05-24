from . handlers import AsyncTask, TaskFailure, TaskTimeout

def setup_goodies():
    from torcel import producer
    producer.setup_producer()