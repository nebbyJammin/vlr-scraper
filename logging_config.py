import logging
from logging.handlers import TimedRotatingFileHandler

import os
from dotenv import load_dotenv

def initialise_logger() -> tuple[logging.Logger, logging.Logger]:
    # Load variables from .env
    load_dotenv()

    #  Get log settings from env
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_RETENTION = int(os.getenv("LOG_RETENTION", 7))

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

    # Stream handler (console)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(LOG_LEVEL)

    # --- Formatter ---
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for h in (file_handler, error_handler, stream_handler):
        h.setFormatter(formatter)
        
    # Configure logger
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            file_handler,
            stream_handler,
        ]
    )

    MAIN_LOGGER = logging.getLogger("Main")
    VLR_LOGGER = logging.getLogger("VLR Scraper")
    PG_LOGGER = logging.getLogger("PG Logger")

    # TODO: Remove -> Silent noisy library
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

    return MAIN_LOGGER, VLR_LOGGER, PG_LOGGER

if __name__ != "__main__":
    MAIN_LOGGER, VLR_LOGGER, PG_LOGGER = initialise_logger()

    MAIN_LOGGER.info("Loggers have been successfully created!")