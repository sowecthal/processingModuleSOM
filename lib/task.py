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
        self.workspace = os.path.join(self.config['MAIN']['workspace'], f'{self.id}')
         
        os.makedirs(self.workspace)
        self.logger.debug('Created directory')
        self.logger.info('Schedule: '+ (', '.join(self.subtasks.keys())))


    async def downloadSubtask(self):
        # TODO: В зависимости от параметра self.config['MAIN']['location'] 
        # копировать или скачивать файл(-ы) из subtasks["download"]. Файлы называть
        # <self.id>_targ.<ext> и <self.id>_ref.<ext>.
        pass


    async def finalSubtask(self):
        # TODO: Вызывать callback URL
        pass


    async def run(self):
        await self.downloadSubtask()
        self.status = "Downloaded"
        await trio.sleep(7)
        self.status = "Completed"
