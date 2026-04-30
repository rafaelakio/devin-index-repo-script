import logging
import logging.config
import os


def setup_logger(verbose: bool = False) -> logging.Logger:
    log_level = logging.DEBUG if verbose else logging.INFO

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "simple": {
                "format": "%(levelname)s - %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "simple",
            },
            "file": {
                "class": "logging.FileHandler",
                "filename": "indexer.log",
                "level": logging.DEBUG,
                "formatter": "detailed",
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": logging.DEBUG,
            "handlers": ["console", "file"],
        },
    })

    return logging.getLogger("devin_indexer")
