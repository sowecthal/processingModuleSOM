import logging
import trio
import sys

from .http import Headers, Request, Response, HTTPError
from .processingTaskManager import ProcessingTaskManager
from .API import API

class Route:
    def __init__(self, method: str, path: str, handler):
        self.method = method
        self.path = path
        self.handler = handler

class CoreProcessingModule:
    def __init__(self, *, logger=None):
        self.logger = logging.getLogger("CORE")
        self.task_manager = ProcessingTaskManager()
        self.routes = []
        self.api_manager = API(self) 
    
    def addRoute(method: str, path: str, handler):
        self.routes.append(method, path, handler)

    def runServe(self, port: int):
        try:
            trio.run(self._serve, port)
        except KeyboardInterrupt:
            sys.exit(0)

    async def _handleConnection(self, conn: trio.SocketStream):
        remote_ip, remote_port, *_ = conn.socket.getpeername()
        
        request = Request(conn)
        response = request.assocResponse

        try:
            await request.receive()
            method, path, headers, data = request.getParams()
            print('net')
            self.logger.info('New %s %s request from %s:%d. Headers: %s; Data: %s' % (method, path, remote_ip, remote_port, str(headers), str(data)))
        except HTTPError as e:
            response.status = e
            response.buildHeaders()
            await response.send()

    async def _serve(self, port: int):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(trio.serve_tcp, self._handleConnection, port)
