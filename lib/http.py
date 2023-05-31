import logging
import trio
import json

class HttpServer:
    routes = {}

    def __init__(self, task_manager, config, logger=logging.getLogger('HTTP')):
        self.task_manager = task_manager
        self.logger = logger
        self.config = config 

    @classmethod 
    def route(self, method, path):
        def decorator(f):
            self.routes[(method, path)] = f
            return f
        return decorator


    async def handleRequest(self, stream):
        data = await stream.receive_some(1024)

        self.logger.debug(f'Received data: {data}')

        headers, body = data.decode('utf-8').split('\r\n\r\n', 1)

        self.logger.debug(f'Headers: {headers}; Body: {body}')

        method, path, _ = headers.split('\r\n')[0].split(' ', 2)
        path_splitted = path.split('/')[1:]
        path_args = {}

        for route, handler in self.routes.items():
            route_method, route_path = route
            if method != route_method:
                continue

            route_path_parts = route_path.split('/')[1:]
            if len(path_splitted) != len(route_path_parts):
                continue

            for route_part, path_part in zip(route_path_parts, path_splitted):
                if route_part.startswith('{') and route_part.endswith('}'):
                    path_args[route_part[1:-1]] = path_part
                elif route_part != path_part:
                    break
            else:
                self.logger.info(f'Start handling {method} {path} request')
                await handler(self, stream, path_args, body)
                return

        self.logger.info(f'Unknown {method} {path} request')
        await stream.send_all(b'HTTP/1.0 404 Not Found\r\n\r\n')


    async def run(self):
        self.logger.info(f"HTTP server is running on port {self.config['MAIN']['port']}")
        await trio.serve_tcp(self.handleRequest, self.config['MAIN']['port'])
