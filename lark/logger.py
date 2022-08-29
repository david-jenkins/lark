
import logging
from logging import handlers
import os
from pathlib import Path
from typing import Union
from inspect import stack

logger_format = logging.Formatter(logging.BASIC_FORMAT)

log_dir = Path("/var/log/lark")

STREAM_LEVEL = "INFO"
FILE_LEVEL = "INFO"

def log_to_stdout(logger=None,level=STREAM_LEVEL):
    streamhandler = logging.StreamHandler()
    streamhandler.setFormatter(logger_format)
    streamhandler.setLevel(logging.getLevelName(level))
    if logger is None: logger = logging.getLogger()
    logger.addHandler(streamhandler)
    return streamhandler

if not log_dir.exists():
    om = os.umask(0o002)
    log_dir.mkdir(mode=0o2777,parents=True)
    os.umask(om)

def addLoggingLevel(levelName, levelNum, methodName=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    
    import logging
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
       raise AttributeError('{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
       raise AttributeError('{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
       raise AttributeError('{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)

addLoggingLevel("STDOUT",logging.INFO+5)
addLoggingLevel("STDERR",logging.INFO+6)

class RotatingFileHandler(handlers.RotatingFileHandler):
    def __init__(self, filename: str, mode: str = 'a', maxBytes: int = 0, backupCount: int = 0, encoding: Union[str, None] = None, delay: bool = False) -> None:
        old_umask = os.umask(0o000)
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        os.umask(old_umask)
    def doRollover(self) -> None:
        old_umask = os.umask(0o000)
        retval = super().doRollover()
        os.umask(old_umask)
        return retval

def log_to_file(name, level=FILE_LEVEL, logger=None):
    filehandler = RotatingFileHandler(log_dir/f'{name}.log',maxBytes=1000000,backupCount=4)
    filehandler.setFormatter(logger_format)
    filehandler.setLevel(logging.getLevelName(level))
    if logger is None: logger = logging.getLogger()
    logger.addHandler(filehandler)
    return filehandler
    

# class MyBaseLogger:
#     def __init__(self, name, level='DEBUG', propagate=True):
#         self.logger = logging.getLogger(name)
#         self.logger.propagate = propagate

#         self.level = logging.getLevelName(level)
#         self.logger.setLevel(self.level)
        
#         self._msg = ''
        
#     def addHandler(self, handler):
#         self.logger.addHandler(handler)

#     def info(self, message, *args, **kwargs):
#         self.logger.info(message,*args,**kwargs)

#     def debug(self, message, *args, **kwargs):
#         self.logger.debug(message,*args,**kwargs)

#     def warn(self, message, *args, **kwargs):
#         self.logger.warn(message,*args,**kwargs)

#     def write(self, message, *args, **kwargs):
#         self._msg = self._msg + message
#         while '\n' in self._msg:
#             pos = self._msg.find('\n')
#             self.logger.log(logging.WARN,self._msg[:pos],*args,**kwargs)
#             self._msg = self._msg[pos+1:]

#     def log(self,level,message):
#         self.logger.log(level, message)

#     def flush(self):
#         if self._msg != '':
#             self.logger.log(self.level,self._msg)
#             self._msg = ''    

# class MyStreamLogger(MyBaseLogger):
#     def __init__(self, name, level='DEBUG', propagate=False):
#         super().__init__(name, level=level, propagate=propagate)

#         self.streamhandler = logging.StreamHandler()
#         self.streamhandler.setFormatter(logger_format)
#         self.streamhandler.setLevel(self.level)
#         self.logger.addHandler(self.streamhandler)


# class MyFileLogger(MyBaseLogger):
#     def __init__(self, name, level='DEBUG', propagate=False):
#         super().__init__(name, level=level, propagate=propagate)

#         self.filehandler = RotatingFileHandler(log_dir/f'{name}.log',maxBytes=1000000,backupCount=4)
#         self.filehandler.setFormatter(logger_format)
#         self.filehandler.setLevel(logging.getLevelName(level))
#         self.logger.addHandler(self.filehandler)


class StreamToLogger:
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger=None, level="DEBUG"):
       self.logger = logger if logger is not None else logging.getLogger()
       self.level = level
       self.linebuf = ''

    def write(self, buf:str):
       for line in buf.rstrip().splitlines():
          self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass
    

# class STACKPRINT_Logger:
#     def __init__(self,logger):
#         self._logger = logger
#     def __getattr__(self, __name: str):
#         return getattr(self.logger, __name)
#     def __setattr__(self, __name: str, __value) -> None:
#         if __name in ["_logger"]:
#             return super().__setattr__(__name,__value)
#         return setattr(self._logger,__name,__value)
#     def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
#         retval = self.logger._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)
#         frameinfo = stack()[3]
#         print(f"\t\"{frameinfo.filename}\", line {frameinfo.lineno}")
#         return retval
        
# def make_logger_STACKPRINT(logger):
#     return STACKPRINT_Logger(logger)

def make_logger_STACKPRINT(logger):
    if not hasattr(logging.Logger, "STACKPRINT"):
        logging.Logger.STACKPRINT = False
        logging.Logger._old_log = logging.Logger._log
        def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
            if not self.STACKPRINT:
                return self._old_log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)
            frameinfo = stack()[3]
            retval = self._old_log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)
            print(f"\t\"{frameinfo.filename}\", line {frameinfo.lineno}")
            return retval
            
        logging.Logger._log = _log
    logger.STACKPRINT = True
