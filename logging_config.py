import logging
from typing import List, Any
from logging.handlers import TimedRotatingFileHandler

import os

def initialise_logger() -> tuple[logging.Logger, logging.Logger, logging.Logger, logging.Logger, logging.Logger]:
    """Initialises loggers and rotating file handlers. Generic logs will go into scraper.log files, while error logs file go into error.log files by default."""
    #  Get log settings from env
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_RETENTION = int(os.getenv("LOG_RETENTION", 7))
    LOG_STDOUT = os.getenv("LOG_STDOUT", 'false').lower() in ("true", "yes", "1")

    # Ensure logs directory exists
    os.makedirs(LOG_DIR, exist_ok=True)

    # File path
    log_file = os.path.join(LOG_DIR, "scraper.log")
    error_log_file = os.path.join(LOG_DIR, "error.log")

    # --- Handlers ---
    # Create rotating file handler (all levels)
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        backupCount=LOG_RETENTION,
        encoding="utf-8",
    )
    file_handler.setLevel(LOG_LEVEL)

    # Create error rotating log (only ERROR and above)
    error_handler = TimedRotatingFileHandler(
        filename=error_log_file,
        when="midnight",
        backupCount=LOG_RETENTION,
        encoding="utf-8",
    )
    error_handler.setLevel("ERROR")

    # --- Formatter ---
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handlers: List[Any] = [file_handler, error_handler] # Add stream_handler if you want to print to stdout

    # Stream handler (console)
    if LOG_STDOUT:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(LOG_LEVEL)
        handlers.append(stream_handler)

    for h in handlers:
        h.setFormatter(formatter)
        
    # Configure logger
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers
    )

    MAIN_LOGGER = logging.getLogger("Main")
    VLR_LOGGER = logging.getLogger("VLR Scraper")
    PG_LOGGER = logging.getLogger("PG Logger")
    PRIVATE_API_LOGGER = logging.getLogger("PRIVATE API")
    UTIL_LOGGER = logging.getLogger("VLR Utils")

    # TODO: Remove -> Silence noisy library
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

    return MAIN_LOGGER, VLR_LOGGER, PG_LOGGER, PRIVATE_API_LOGGER, UTIL_LOGGER


MAIN_LOGGER, VLR_LOGGER, PG_LOGGER, PRIVATE_API_LOGGER, UTIL_LOGGER = initialise_logger()

MAIN_LOGGER.info("Loggers have been successfully created!")
