import trio
import uuid
import os

class Task:
    def __init__(self, subtasks: dict):
        self.id = uuid.uuid4().hex
        self.status = "Created"\
        self.subtasks = subtasks
        # TODO: Передавать сюда также нужные URL и PATH
        # TODO: Придумать как обрабатывать subtasks и как они должны выглядеть.
        # TODO: Создавать папку с именем равным id задачи в ../var/workspace.
        # TODO: В эту папку скачивать(копировать) файл, называть его id задачи. PATH файла записать в self.ПЕРЕМЕННУЮ

    async def run(self):
        await trio.sleep(7)
        self.status = "Processing"
        await trio.sleep(7)
        self.status = "Completed"
