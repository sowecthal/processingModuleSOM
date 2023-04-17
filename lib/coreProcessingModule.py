import logging
import trio
import sys

from .http import Headers, Request, Response, HTTPError
from .processingTaskManager import ProcessingTaskManager

class CoreProcessingModule:
    def __init__(self, *, logger=None):
        self.task_manager = ProcessingTaskManager()
    
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
            print(method, path, headers, data)
        except HTTPError as e:
            response.status = e
            response.buildHeaders()
            await response.send()

    async def _serve(self, port: int):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(trio.serve_tcp, self._handleConnection, port)
