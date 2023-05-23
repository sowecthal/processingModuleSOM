import trio


class Task:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = "Created"

    async def run(self):
        await trio.sleep(1)
        self.status = "Processing"
        await trio.sleep(1)
        self.status = "Completed"
