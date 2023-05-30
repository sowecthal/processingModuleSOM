import logging
import trio
import json
import sys

from .http import HttpServer
from .taskManager import TaskManager
from .task import Task

task_manager = TaskManager()
server = HttpServer(task_manager)


@server.route('POST', '/startProc')
async def start_task(stream, path_args: dict = {}, body: str = ''): 
    try:
        body_dict = json.loads(body)
    except json.JSONDecodeError:
        await stream.send_all(b'HTTP/1.0 400 Bad request\r\n\r\nJSON load error\n')
        return

    task = Task(dict())
    await task_manager.new_tasks_queue.put(task)
    await stream.send_all("HTTP/1.0 200 OK\r\n\r\n{'task_id': %s}\n" % task.id)

@server.route('GET', '/getProcInfo/{id}')
async def get_task_info(stream, path_args: dict = {}, body: str = ''):
    status = task_manager.get_task_status(task_id)
    await stream.send_all(f'HTTP/1.0 200 OK\r\n\r\nTask Status: {status}\n'.encode('utf-8'))


async def run():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(server.run)
        nursery.start_soon(task_manager.process_tasks)

