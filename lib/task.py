import logging
import shutil
import trio
import asks
import uuid
import os


class Task:
    def __init__(self, subtasks: dict, config: dict, logger=None):
        self.id = uuid.uuid4().hex
        self.subtasks = subtasks
        self.config = config
        self.logger = logger if logger else logging.getLogger(f'TASK_{self.id}')
        self.workspace = os.path.join(self.config['MAIN']['workspace'], f'{self.id}')
        self.location = self.config['MAIN']['location']

        self.status = 'Created'
        self.comment = 'Success'
        self.target_path = ''
        self.reference_path = ''
        self.last_path = ''

        os.makedirs(self.workspace)
        self.logger.debug('Created directory')
        self.logger.info('Schedule: '+ (', '.join(self.subtasks.keys())))


    async def copyFileInWorkspace(self, path: str, prefix: str = '') -> (bool, str):
        try:
            ext = path.split('.')[-1]
            dst = os.path.join(self.workspace, f'{prefix}_{self.id}' + '.' + ext)
            shutil.copy2(path, dst)
            return True, str(dst)
        except Exception as e:
            self.logger.info(f'Copy error: "{str(e)}"')
            return False, ''
        

    async def downloadFileInWorkspace(self, url: str, prefix: str) -> (bool, str):
        try:
            ext = ext = url.split('.')[-1]
            resp = await asks.get(url)
            
            if resp.status_code != 200:
                return False, ''
            
            dst = os.path.join(self.workspace, f'{prefix}_{self.id}' + '.' + ext)
            with open(dst, 'wb') as f:
                f.write(resp.content)
            return True, dst
        
        except Exception as e:
            self.logger.info(f'Download error: "{str(e)}"')
            return False, ''


    async def runDownloadSubtask(self, *args) -> (bool, str):
        targ = self.subtasks['download'].get('target')
        ref = self.subtasks['download'].get('reference')

        if self.location == 'remote':
            targ_download_ok = False
            ref_download_ok = True
            if targ:
                targ_download_ok, self.target_path = await self.downloadFileInWorkspace(targ, 'targ')

            if ref:
                ref_download_ok, self.reference_path = await self.downloadFileInWorkspace(ref, 'ref')
            
            if not targ_download_ok or not ref_download_ok:
                return False, 'Error while downloading file'

        elif self.location == 'local':
            targ_copy_ok = False
            ref_copy_ok = True
            if targ:
                targ_copy_ok, self.target_path = await self.copyFileInWorkspace(targ, 'targ')

            if ref:
                ref_copy_ok, self.reference_path = await self.copyFileInWorkspace(ref, 'ref')

            if not targ_copy_ok or not ref_copy_ok:
                return False, 'Error while copying file'
        
        else:
            return False, 'Unknown "location" value'
        
        return True, self.target_path
        

    async def runFinalSubtask(self, *args) -> (bool, str):
        path = args[0]
        self.logger.debug(f'Inside the "runFinalSubtask" with "{path}" path')
        if self.location == 'remote':
            with open(path, 'rb') as f:
                data = f.read()

        elif self.location == 'local':
            data = path

        else:
            return False, 'Unknown "location" value'

        try:
            resp = None
            with trio.move_on_after(5):
                resp = await asks.post(self.subtasks['final']['callback'], data=data)

            if resp and resp.status_code != 200:
                return False, 'Unsuccessfull callback HTTP status code'
        except Exception as e:
            return False, f'Unsuccessfull callback request with error: {str(e)}'
        
        return True, 'Success'


    async def runEqualizeSubtask(self, *args) -> (bool, str):
        path = args[0]
        

    async def runSubtask(self, subtask_name, *args) -> (bool, str):
        end_status, handler = subtasks_info.get(subtask_name, (None, None))
        
        ok = False
        comment = 'Not supported subtask name'

        if handler:
            self.logger.debug(f'Start "{subtask_name}" subtask')
            ok, comment = await handler(self, *args)

        if not ok:
            self.status = 'Error'
            self.comment = comment
            self.logger.debug(f'Changed status to "Error", with comment: {comment}')
            return False, comment

        self.status = end_status
        self.logger.info(f'Changed status to "{end_status}"')
        return True, comment


    async def run(self):
        comment = ''
        for subtask_name in self.subtasks.keys():
            ok, comment = await self.runSubtask(subtask_name, comment)
            if not ok:
                break
        else:
            self.logger.warning(f'is done')


# Rows should look like '<subtask_name>': ('<end_status>', <handler>)
subtasks_info = {
   'download': ('Downloaded', Task.runDownloadSubtask),
   'equalize': ('Equalized', Task.runEqualizeSubtask),
    # TODO: Добавить все подзадачи и их обработчики
    # TODO: Oбработчики gодзадач мастеринга, каждый возвращает два значения ok: bool и 
    #       comment: str (Пояснение ошибки или путь результирующего файла, который 
    #       необходимо передать в следующую функцию)
    'final': ('Done', Task.runFinalSubtask)
}
