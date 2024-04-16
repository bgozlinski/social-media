from logging.config import dictConfig
from src.config import DevConfig, config


def configure_logging() -> None:
    level = "DEBUG" if isinstance(config, DevConfig) else "INFO"
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
                "level": level,
            },

            "loggers": {
                "src": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": False,

                }
            }
        }
    )