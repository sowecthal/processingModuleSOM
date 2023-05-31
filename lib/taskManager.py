import logging
import trio
import os

from .task import Task


class Queue:
    def __init__(self):
        self._items = []
        self._event = trio.Event()

    async def put(self, item):
        self._items.append(item)
        self._event.set()
        return

    async def get(self):
        await self._event.wait()
        item = self._items.pop(0)
        if not self._items:
            self._event = trio.Event()
        return item


class TaskManager:
    def __init__(self, logger=logging.getLogger('TASK_MANAGER')):
        self.tasks = dict()
        self.logger = logger
        self.new_tasks_queue = Queue()


    async def processTasks(self):
        self.logger.info('Task manager is running')
        while True:
            task = await self.new_tasks_queue.get()
            self.tasks[task.id] = task
            trio.lowlevel.spawn_system_task(task.run)


    def getTaskStatus(self, task_id: str) -> str:
        if task_id in self.tasks:
            return self.tasks[task_id].status

