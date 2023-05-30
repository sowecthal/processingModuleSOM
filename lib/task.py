import trio
import uuid

class Task:
    def __init__(self, subtasks: dict):
        self.id = uuid.uuid4().hex
        self.status = "Created"


    async def run(self):
        await trio.sleep(7)
        self.status = "Processing"
        await trio.sleep(7)
        self.status = "Completed"
