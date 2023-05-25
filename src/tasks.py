from src.transcript import transcribe
from celery import Celery

app = Celery('worker', broker='pyamqp://guest@localhost//', backend='rpc://')

@app.task(name='transcribe_task')
def transcribe_task(file_path:str):
    transcript = transcribe(file_path)
    return transcript