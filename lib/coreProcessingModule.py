import logging
import trio
import sys

from .networking import Headers, Request, Response, HTTPError
from .API import task_manager

class CoreProcessingModule:
    def __init__(self):
        self.logger = logging.getLogger("CORE")
        self.task_manager = task_manager
        self.routes = []
    
    def run(self, port: int):
        try:
            trio.run(self._run, port)
        except KeyboardInterrupt:
            sys.exit(0)

    async def _handleConnection(self, conn: trio.SocketStream):
        remote_ip, remote_port, *_ = conn.socket.getpeername()
        
        request = Request(conn)
        response = request.assocResponse

        try:
            await request.receive()
            method, path, headers, data = request.getParams()
            self.logger.info('New %s %s request from %s:%d. Headers: %s; Data: %s' % (method, path, remote_ip, remote_port, str(headers), str(data)))
        except HTTPError as e:
            response.status = e
            response.buildHeaders()
            await response.send()

    async def _run(self, port: int):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(trio.serve_tcp, self._handleConnection, port)
