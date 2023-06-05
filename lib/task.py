import logging
import shutil
import trio
import asks
import uuid
import os
import re

from .mastering import equalizeFile, compressFile, normalizeFile, byReference

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
        self.logger.debug('Inside the "runDownloadSubtask" function')

        targ = self.subtasks['download'].get('target')
        ref = self.subtasks['download'].get('reference')

        targ_is_url = re.match(r'http(s)?:\/\/.*', str(targ))
        ref_is_url = re.match(r'http(s)?:\/\/.*', str(ref))

        if targ:
            targ_ok, comment = await self.downloadFileInWorkspace(targ, 'targ') if targ_is_url else await self.copyFileInWorkspace(targ, 'targ')

            if targ_ok:
                self.target_path = comment
            else:
                return False, 'Error while downloading or copying target file'
        else:
            return False, 'Target file location is a mandatory parameter'

        if ref:
            ref_ok, comment = await self.downloadFileInWorkspace(ref, 'ref') if ref_is_url else await self.copyFileInWorkspace(ref, 'ref')

            if ref_ok:
                self.reference_path = comment
            else:
                return False, 'Error while downloading or copying reference file'
        
        return True, self.target_path
        

    async def runEqualizeSubtask(self, *args) -> (bool, str):
        self.logger.debug('Inside the "runEqualizeSubtask" function')

        path = args[0]
        try:
            equalization_params = self.subtasks['equalize']
            #sequalized_file_path = equalizeFile(path, equalization_params)
            equalized_file_path = await trio.to_thread.run_sync(equalizeFile, path, equalization_params)
            self.logger.debug(f'\tequalized_file_path: {equalized_file_path}')
            return True, equalized_file_path
        except Exception as e:
            return False, f'Error in equalization: {str(e)}'
        

    async def runCompressionSubtask(self, *args) -> (bool, str):
        self.logger.debug('Inside the "runCompressionSubtask" function')

        path = args[0]
        try:
            compression_params = self.subtasks['compress']
            compressed_file_path = compressFile(path, **compression_params)

            return True, compressed_file_path
        except Exception as e:
            return False, f'Error in compression: {str(e)}'


    async def runNormalizationSubtask(self, *args) -> (bool, str):
        self.logger.debug('Inside the "runNormalizationSubtask" function')

        path = args[0]
        try:
            normalization_params = self.subtasks['normalize']
            normalized_file_path = normalizeFile(path, **normalization_params)
            
            return True, normalized_file_path
        except Exception as e:
            self.logger.error(f'Error in normalization: {str(e)}')
            return False, f'Error in normalization: {str(e)}'


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
                

    async def runSubtask(self, subtask_name, *args) -> (bool, str):
        end_status, handler = subtasks_info.get(subtask_name, (None, None))
        
        ok = False
        comment = 'Not supported subtask name'

        if handler:
            self.logger.info(f'Start "{subtask_name}" subtask')
            ok, comment = await handler(self, *args)
            self.logger.debug(f'Out of handler function with ok: {ok} and comment: {comment}')

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
                self.logger.warning(f'Bad subtask result. Comment: {comment}')
                break
        else:
            self.logger.info(f'All subtasks completed successfully')


# Rows should look like '<subtask_name>': ('<end_status>', <handler>)
subtasks_info = {
   'download': ('Downloaded', Task.runDownloadSubtask),
   'equalize': ('Equalized', Task.runEqualizeSubtask),
   'compression': ('Compressed', Task.runCompressionSubtask),
   'normalize': ('Normalized', Task.runNormalizationSubtask),
    # TODO: Добавить все подзадачи и их обработчики
    # TODO: Oбработчики подзадач мастеринга, каждый возвращает два значения ok: bool и 
    #       comment: str (Пояснение ошибки или путь результирующего файла, который 
    #       необходимо передать в следующую функцию)
    'final': ('Done', Task.runFinalSubtask)
}
