import logging
import shutil
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


    async def copyFileInWorkspace(self, src: str, suffix: str = '') -> bool:
        try:
            ext = src.split('.')[-1]
            dst = os.path.join(self.workspace, f'{self.id}_{suffix}' + '.' + ext)
            await trio.to_thread.run_sync(shutil.copy2, src, dst)
            return True
        except:
            return False


    async def downloadSubtask(self) -> (bool, str):
        # TODO: В зависимости от параметра self.config['MAIN']['location'] 
        # копировать или скачивать файл(-ы) из subtasks["download"]. Файлы называть
        # <self.id>_targ.<ext> и <self.id>_ref.<ext>.

        location = self.config['MAIN']['location']
        targ = self.subtasks['download'].get('target')
        ref = self.subtasks['download'].get('reference')


        if location == 'remote':
            if targ:
                # Синхронные функции можно заворачивать в await trio.to_thread.run_sync(func, *args)
                pass

            if ref:
                # Синхронные функции можно заворачивать в await trio.to_thread.run_sync(func, *args)
                pass

        elif location == 'local':  
            if targ:
                targ_copy_ok = await self.copyFileInWorkspace(targ, 'targ')

            if ref:
                ref_copy_ok = await self.copyFileInWorkspace(ref, 'ref')

            if not targ_copy_ok or not ref_copy_ok:
                return False, 'Error while copying file'
        else:
            return False, 'Unknown "location" value'
        
        return True, ''
        

    async def finalSubtask(self):
        # TODO: Вызывать callback URL
        pass


    async def run(self):
        await self.downloadSubtask()
        self.status = "Downloaded"
        await trio.sleep(7)
        self.status = "Completed"
