import logging
import trio
import sys

from .http import Headers, Request, Response, HTTPError
from .processingTaskManager import ProcessingTaskManager
from .API import API


task_manager = TaskManager()
server = HttpServer(task_manager)


@server.route('GET', '/getProcInfo')
async def get_task_info(task_manager, stream, task_id):
    status = task_manager.get_task_status(task_id)
    await stream.send_all(f'HTTP/1.0 200 OK\r\n\r\nTask Status: {status}\n'.encode('utf-8'))

@server.route('POST', '/startProc')
async def start_task(task_manager, stream, task_id):
    await task_manager.task_queue.put(task_id)
    await stream.send_all(b'HTTP/1.0 200 OK\r\n\r\nTask creation started\n')

async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(server.run)
        nursery.start_soon(task_manager.process_tasks)

