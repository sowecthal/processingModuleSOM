import trio
from collections import defaultdict
from trio.lowlevel import ParkingLot
import json


class HttpServer:
    def __init__(self, task_manager, config, logger):
        self.task_manager = task_manager
        self.logger = logger
        self.config = config
        self.routes = {}

    def route(self, method, path):
        def decorator(f):
            self.routes[(method, path)] = f
            return f
        return decorator

    async def handle_request(self, stream):
        data = await stream.receive_some(1024)
        headers, body = data.decode('utf-8').split('\r\n\r\n', 1)

        method, path, _ = headers.split('\r\n')[0].split(' ', 2)
        path = path.split('/')[1]
        handler = self.routes.get((method, path))

        if handler:
            task_id = body.strip() if method == 'POST' else path.split('/')[-1]
            await handler(self.task_manager, stream, task_id)
        else:
            await stream.send_all(b'HTTP/1.0 404 Not Found\r\n\r\n')

    async def run(self):
        await trio.serve_tcp(self.handle_request, 8000)
