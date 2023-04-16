import logging
import trio
import sys

from .processingTaskManager import ProcessingTaskManager

class CoreProcessingModule:
    def __init__(self, *, logger=None):
        pass
    
    def runServe(self, port: int):
        try:
            trio.run(self._serve, port)
        except KeyboardInterrupt:
            sys.exit(0)

    async def _handleConnection(self, conn):
        print(1)
        pass

    async def _serve(self, port: int):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(trio.serve_tcp, self._handleConnection, port)

    def main():
        pass