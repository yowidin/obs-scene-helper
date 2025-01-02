import logging

from typing import Optional

from obs_scene_helper.model.log.table import Table as LogTable


class LogHandler(logging.Handler):
    def __init__(self, model: LogTable):
        super().__init__()
        self._model = model

    def emit(self, record: logging.LogRecord):
        self._model.add_record(record)


class Log:
    INSTANCE = None  # type: Optional[Log]
    LOGGER_NAME = 'osh'

    def __init__(self):
        self.logger = logging.getLogger(Log.LOGGER_NAME)
        self.logger.setLevel(logging.DEBUG)

        self.model = LogTable()

        self.handler = LogHandler(self.model)
        self.logger.addHandler(self.handler)

    @staticmethod
    def setup():
        if Log.INSTANCE is None:
            Log.INSTANCE = Log()

    @staticmethod
    def child(name: str):
        return Log.INSTANCE.logger.getChild(name)
