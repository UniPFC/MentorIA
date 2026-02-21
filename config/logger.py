import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from config.settings import settings

class ColoredFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    orange = "\x1b[33;20m"
    red = "\x1b[31;20m"
    blood_red = "\x1b[91;1m"
    reset = "\x1b[0m"

    format_str = "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: blue + format_str + reset,
        logging.WARNING: orange + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: blood_red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

def setup_logger():
    if not os.path.exists(settings.LOG_DIR):
        os.makedirs(settings.LOG_DIR)

    logger_name = getattr(settings, "PROJECT_NAME", "GitGudGuide")
    logger = logging.getLogger(logger_name)
    
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        return logger

    console_handler = logging.StreamHandler(sys.stdout)
    console_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ColoredFormatter())

    log_file_path = os.path.join(settings.LOG_DIR, "app.log")
    
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=10 * 1024 * 1024,
        backupCount=5, 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()