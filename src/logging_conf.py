from logging.config import dictConfig
from src.config import DevConfig, config


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                    "format":  "%(name)s:%(lineno)d - %(message)s"
                }
            },

            "handlers": {
                "default": {
                    "class": "rich.logging.RichHandler",
                    "level": "DEBUG",
                    "formatter": "console",
                }
            },

            "root": {
                "handlers": ["default"],
                "level": "DEBUG" if isinstance(config, DevConfig) else "INFO",
            },

            "loggers": {
                "uvicorn": {
                    "handlers": ["default"],
                    "level": "INFO",
                },
                "src": {
                    "handlers": ["default"],
                    "level": "DEBUG" if isinstance(config, DevConfig) else "INFO",
                    "propagate": False,

                },
                "databases": {
                    "handlers": ["default"],
                    "level": "WARNING"
                },
                "aiosqlite": {
                    "handlers": ["default"],
                    "level": "WARNING"
                }
            }
        }
    )
