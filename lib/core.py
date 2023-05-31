import logging
import trio
import json
import sys

from .http import HttpServer
from .taskManager import TaskManager
from .task import Task


@HttpServer.route('POST', '/startProc')
async def startTask(server, stream, path_args: dict = {}, body: str = ''):
    server.logger.debug('Inside the "startTask" function')
    try:
        body_dict = json.loads(body)
    except json.JSONDecodeError:
        await stream.send_all(b'HTTP/1.0 400 Bad request\r\n\r\nJSON load error\n')
        return
    
    # TODO: Обрабатывать JSON, он хранится в переменной body_dict
    subtasks = {}
    task = Task(subtasks, server.config, server.logger) # TODO: Вместо пустого dict() - передавать словарь подзадач
    await server.task_manager.new_tasks_queue.put(task)

    await stream.send_all(f'HTTP/1.0 200 OK\r\n\r\n{task.id}\n'.encode('utf-8'))


@HttpServer.route('GET', '/getProcInfo/{id}')
async def getTaskInfo(server, stream, path_args: dict = {}, body: str = ''):
    server.logger.debug('Inside the "getTaskInfo" function')
    status = server.task_manager.get_task_status(path_args['id'])
    # TODO: Добавить проверку ненулевого статуса. Если он None, то возвращать HTTP 404 Not found

    if status is None:
        response = 'HTTP/1.0 404 Not Found\r\n\r\nTask Not Found\n'.encode('utf-8')
    else:
        response = f'HTTP/1.0 200 OK\r\n\r\n{status}\n'.encode('utf-8')
    
    await stream.send_all(response)


class Core:
    def __init__(self, config):
        self.task_manager = TaskManager()
        self.server = HttpServer(self.task_manager, config)


    async def run(self):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.task_manager.processTasks)
            nursery.start_soon(self.server.run)
            

