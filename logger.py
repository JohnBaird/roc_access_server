# updated: 2025-04-26 14:47:01
# created: 2024-08-31 22:05:00
# filename: logger.py
#-----------------------------------------------------------------------------------------------------------------------------
import re
import logging
from logging.handlers import RotatingFileHandler
#-----------------------------------------------------------------------------------------------------------------------------
class CustomLogger:
    def __init__(
            self,
            backup_count = 5,
            max_bytes = 10485760,
            logfile = "default_logfile.log",
            logger_level = "INFO",
            util_prt = False,
            util_prt0 = False
        ):

        self.util_prt = util_prt
        self.util_prt0 = util_prt0
        
        # Set log level from config
        log_level_str = logger_level.upper()
        log_level = getattr(logging, log_level_str, logging.DEBUG)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)

        self.formatter = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")

        self.file_handler = RotatingFileHandler(
            logfile, mode='a', maxBytes=max_bytes, backupCount=backup_count
        )
        self.file_handler.setLevel(log_level)
        self.file_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.file_handler)

    # --------------------------------------------------
    def exclude_debug_entries(self, pattern):
        class ExcludeFilter(logging.Filter):
            def __init__(self, pattern):
                self.pattern = re.compile(pattern)

            def filter(self, record):
                return not (
                    record.levelno == logging.DEBUG and self.pattern.match(record.msg)
                )

        self.logger.addFilter(ExcludeFilter(pattern))

    # --------------------------------------------------
    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

    # --------------------------------------------------
    def log_debug (self, msg):
        self.logger.debug (msg)
        if self.util_prt0:
            print (msg)

    def log_info (self, msg):
        self.logger.info (msg)
        if self.util_prt0:
            print (msg)

    def log_warning (self, msg):
        self.logger.warning (msg)
        if self.util_prt0:
            print (msg)

    def log_error (self, msg):
        self.logger.error (msg)
        if self.util_prt0:
            print (msg)

    def log_critical (self, msg):
        self.logger.critical (msg)
        if self.util_prt0:
            print (msg)

#-----------------------------------------------------------------------------------------------------------------------------