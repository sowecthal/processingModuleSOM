import logging
import trio
import uuid
import os

class Task:
    def __init__(self, subtasks: dict, config: dict, logger=None):
        self.id = uuid.uuid4().hex
        self.status = "Created"
        self.subtasks = subtasks
        self.config = config
        self.logger = logger if logger else logging.getLogger(f'TASK_{self.id}')

        self.logger.info("I'm created")

        os.makedirs(self.config['MAIN']['workspace'], exist_ok=True)

        # TODO: Передавать сюда также нужные URL и PATH
        # TODO: Придумать как обрабатывать subtasks и как они должны выглядеть.
        # TODO: Создавать папку с именем равным id задачи в ../var/workspace.

    async def downloadFile(self):
        self.file_path = os.path.join(self.directory, f'{self.id}')
        # TODO: В эту папку скачивать(копировать) файл, называть его id задачи. PATH файла записать в self.ПЕРЕМЕННУЮ

    async def run(self):
        await trio.sleep(7)
        self.status = "Processing"
        await trio.sleep(7)
        self.status = "Completed"
