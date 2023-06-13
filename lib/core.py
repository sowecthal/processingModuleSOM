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
    except json.JSONDecodeError as e:
        server.logger.error(f'JSON load error: {str(e)}. Send 400 Bad Request')
        await stream.send_all(f'HTTP/1.0 400 Bad Request\r\n\r\nJSON load error\n'.encode('utf-8'))
        return
    
    subtasks = dict()

    subtasks['download'] = {'target': body_dict.get('targetTrack')}
    callback = body_dict.get('callbackURL')

    if not subtasks['download']['target'] or not callback or 'masteringOperations' not in body_dict.keys():
        server.logger.error(f'JSON is incorrect: {str(e)}. Send 400 Bad Request')
        await stream.send_all(b'HTTP/1.0 400 Bad Request\r\n\r\nJSON is incorrect\n')
        return

    find = lambda opers, key: next((item for item in opers if item['type'] == key), None)

    try:
        if reference := find(body_dict['masteringOperations'], 'reference'):
            subtasks['download']['reference'] = reference['params']['referenceTrack']
            subtasks['reference'] = reference['params']
        else:
            if equalize := find(body_dict['masteringOperations'], 'equalization'):
                subtasks['equalize'] = {k: group.get('gain', 0) for group in equalize['params'] for k in group['frequencies']}
            
            if compression := find(body_dict['masteringOperations'], 'compression'):
                subtasks['compress'] = compression['params']

            if normalization := find(body_dict['masteringOperations'], 'normalization'):
                subtasks['normalize'] = normalization['params']
    except Exception as e:
        server.logger.error(f'Bad masteringOperations structure: {str(e)}. Send 400 Bad Request')
        await stream.send_all(f'HTTP/1.0 400 Bad Request\r\n\r\nBad masteringOperations structure\n'.encode('utf-8'))
        return

    subtasks['final'] = {'callback': callback}

    task = Task(subtasks, server.config)
    await server.task_manager.new_tasks_queue.put(task)

    await stream.send_all(f'HTTP/1.0 200 OK\r\n\r\n{task.id}\n'.encode('utf-8'))
    server.logger.debug(f'End of the "startTask" function')


@HttpServer.route('GET', '/getProcInfo/{id}')
async def getTaskInfo(server, stream, path_args: dict = {}, body: str = ''):
    server.logger.debug('Inside the "getTaskInfo" function')
    status = server.task_manager.get_task_status(path_args['id'])

    if status is None:
        server.logger.error(f'Task Not Found. Send 200 OK')
        response = b'HTTP/1.0 404 Not Found\r\n\r\nTask Not Found\n'
    else:
        response = f'HTTP/1.0 200 OK\r\n\r\n{status}\n'.encode('utf-8')
    
    await stream.send_all(response)
    server.logger.debug(f'End of the "getTaskInfo" function')


@HttpServer.route('POST', '/test/callback')
async def testCallback(server, stream, path_args: dict = {}, body: str = ''):
    server.logger.debug('Inside the "testCallback" function')
    server.logger.info(f'Callback received: {body}')
    await stream.send_all(b'HTTP/1.0 200 OK\r\n\r\n')


class Core:
    def __init__(self, config):
        self.task_manager = TaskManager()
        self.server = HttpServer(self.task_manager, config)


    async def run(self):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.task_manager.processTasks)
            nursery.start_soon(self.server.run)
            

