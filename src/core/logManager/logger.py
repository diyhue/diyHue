import logging


def _get_log_format():
    return logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class Logger:
    loggers = {}
    logLevel = logging.DEBUG # Capture all logs prior to switching

    def configure_logger(self, level):
        self.logLevel = getattr(logging, level)

        for loggerName in self.loggers:
            self.loggers[loggerName].handlers.clear()
            self._setup_logger(loggerName)

    def _setup_logger(self, name):
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(_get_log_format())
        logger.setLevel(self.logLevel)
        logger.addHandler(handler)
        logger.propagate = False
        return logger

    def get_logger(self, name):
        if name not in self.loggers:
            self.loggers[name] = self._setup_logger(name)
        return self.loggers[name]
