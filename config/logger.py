import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

from config.settings import settings


class SourceFilter(logging.Filter):
    """Filter to add source tag to log records."""
    def filter(self, record):
        # Determine source based on logger name
        logger_name = record.name

        if logger_name.startswith("uvicorn"):
            record.source = "WEB"
        elif logger_name.startswith("alembic"):
            record.source = "DBA"
        elif logger_name.startswith(settings.PROJECT_NAME):
            record.source = "APP"
        elif logger_name.startswith("sqlalchemy"):
            record.source = "SQL"
        else:
            record.source = "SYS"

        return True

class ColoredFormatter(logging.Formatter):
    # Level colors
    grey = "\x1b[90m"
    blue = "\x1b[34;20m"
    orange = "\x1b[33;20m"
    red = "\x1b[31;20m"
    blood_red = "\x1b[91;1m"
    reset = "\x1b[0m"

    # Fixed color for timestamp
    timestamp_color = "\x1b[90;20m"  # Dark grey

    # Source colors
    web_color = "\x1b[36;20m"     # Cyan
    dba_color = "\x1b[33;20m"     # Yellow
    app_color = "\x1b[32;20m"     # Green
    sql_color = "\x1b[35;20m"     # Magenta (Purple)
    sys_color = "\x1b[37;20m"     # White

    SOURCE_COLORS = {
        "WEB": web_color,
        "DBA": dba_color,
        "APP": app_color,
        "SQL": sql_color,
        "SYS": sys_color
    }

    FORMATS = {
        logging.DEBUG: grey,
        logging.INFO: blue,
        logging.WARNING: orange,
        logging.ERROR: red,
        logging.CRITICAL: blood_red
    }

    def __init__(self):
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")

    def formatTime(self, record, datefmt=None):
        # Use UTC-3 (Brazil timezone) hardcoded for Docker container
        offset_str = "UTC-3"

        # Format timestamp
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime(self.default_time_format, ct)
            s = str(self.default_msec_format) % (t, record.msecs)

        return f"{s} {offset_str}"

    def format(self, record):
        # Get level color
        level_color = self.FORMATS.get(record.levelno, self.grey)

        # Get source color
        source_color = self.SOURCE_COLORS.get(getattr(record, 'source', 'SYS'), self.sys_color)

        # Use source and level as-is without padding
        source = getattr(record, 'source', 'SYS')

        # Abbreviate level
        level_map = {
            'DEBUG': 'DEBUG',
            'INFO': 'INFO',
            'WARNING': 'WARN',
            'ERROR': 'ERROR',
            'CRITICAL': 'CRIT'
        }
        level = level_map.get(record.levelname, record.levelname[:4])

        # Format with custom format string
        colored_format = (
            f"{self.timestamp_color}[%(asctime)s]{self.reset} {source_color}[{source}]{self.reset} "
            f"{level_color}[{level}]{self.reset} "
            f"{level_color}[%(filename)s:%(lineno)d]{self.reset} - {level_color}%(message)s{self.reset}"
        )

        # Use parent class to format with our custom formatTime
        self._style._fmt = colored_format
        return super().format(record)


class UTCOffsetFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # Use UTC-3 (Brazil timezone) hardcoded for Docker container
        offset_str = "UTC-3"

        # Format timestamp
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime(self.default_time_format, ct)
            s = str(self.default_msec_format) % (t, record.msecs)

        return f"{s} {offset_str}"


def setup_logger():
    if not os.path.exists(settings.LOG_DIR):
        os.makedirs(settings.LOG_DIR)

    console_handler = logging.StreamHandler(sys.stdout)
    console_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ColoredFormatter())
    console_handler.addFilter(SourceFilter())

    log_file_path = os.path.join(settings.LOG_DIR, "app.log")
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(console_level)
    file_formatter = UTCOffsetFormatter(
        "[%(asctime)s] [%(source)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(SourceFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logger_name = getattr(settings, "PROJECT_NAME", "GitGudGuide")
    return logging.getLogger(logger_name)

logger = setup_logger()
