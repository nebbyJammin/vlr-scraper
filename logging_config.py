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

    # Create rotating file handler
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        backupCount=LOG_RETENTION,
        encoding="utf-8",
    )
        
    # Configure logger
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            file_handler,
            logging.StreamHandler()
        ]
    )

    MAIN_LOGGER = logging.getLogger("Main")
    VLR_LOGGER = logging.getLogger("VLR Scraper")

    return MAIN_LOGGER, VLR_LOGGER

if __name__ != "__main__":
    MAIN_LOGGER, VLR_LOGGER = initialise_logger()

    MAIN_LOGGER.info("Loggers have been successfully created!")