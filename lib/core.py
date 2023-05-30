import logging
import trio
import json
import sys

from .http import HttpServer
from .taskManager import TaskManager
from .task import Task


@HttpServer.route('POST', '/startProc')
async def start_task(server, stream, path_args: dict = {}, body: str = ''): 
    try:
        body_dict = json.loads(body)
    except json.JSONDecodeError:
        await stream.send_all(b'HTTP/1.0 400 Bad request\r\n\r\nJSON load error\n')
        return
    
    # TODO: Обрабатывать JSON, он хранится в переменной body_dict

    task = Task(dict()) # TODO: Вместо пустого dict() - передавать словарь подзадач
    await server.task_manager.new_tasks_queue.put(task)

    await stream.send_all(f'HTTP/1.0 200 OK\r\n\r\n{task.id}\n'.encode('utf-8'))


@HttpServer.route('GET', '/getProcInfo/{id}')
async def get_task_info(server, stream, path_args: dict = {}, body: str = ''):
    status = server.task_manager.get_task_status(path_args['id'])
    # TODO: Добавить проверку ненулевого статуса. Если он None, то возвращать HTTP 404 Not found
    await stream.send_all(f'HTTP/1.0 200 OK\r\n\r\nTask Status: {status}\n'.encode('utf-8'))


class Core:
    def __init__(self, config, logger):
        self.task_manager = TaskManager() # TODO: Передавать внуть logger
        self.server = HttpServer(self.task_manager, config, logger)


    async def run(self):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.server.run)
            nursery.start_soon(self.task_manager.process_tasks)

