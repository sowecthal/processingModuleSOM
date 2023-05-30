from collections import defaultdict
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
    def __init__(self):
        self.tasks = defaultdict(Task)
        self.new_tasks_queue = Queue()
        

    async def process_tasks(self):
        while True:
            task = await self.new_tasks_queue.get()
            self.tasks[task.id] = task
            trio.lowlevel.spawn_system_task(task.run)


    def get_task_status(self, task_id: str) -> str:
        if task_id in self.tasks:
            return self.tasks[task_id].status

