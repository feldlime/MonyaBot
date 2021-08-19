import logging.config
import typing as tp

from .settings import ServiceConfig

app_logger = logging.getLogger("app")

ACCESS_LOG_FORMAT = (
    'remote_addr="%a" '
    'referer="%{Referer}i" '
    'user_agent="%{User-Agent}i" '
    'protocol="%r" '
    'response_code="%s" '
    'request_time="%Tf" '
)


class TgMsgInfoFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        setattr(record, "chat_id", "chat_id")
        setattr(record, "username", "username")
        setattr(record, "message_id", "message_id")
        return super().filter(record)


def get_config(service_config: ServiceConfig) -> tp.Dict[str, tp.Any]:
    level = service_config.log_config.level
    datetime_format = service_config.log_config.datetime_format

    config = {
        "version": 1,
        "disable_existing_loggers": True,
        "loggers": {
            "root": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
            app_logger.name: {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "handlers": {
            "console": {
                "formatter": "console",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "filters": ["tg_msg_info"],
            },
        },
        "formatters": {
            "console": {
                "format": (
                    '%(asctime)s '
                    '- %(levelname)s '
                    '- pid=%(process)d '
                    # 'chat_id="%(chat_id)s" '
                    # 'username="%(username)s" '
                    # 'message_id="%(message_id)s" '
                    '| %(message)s'
                ),
                "datefmt": datetime_format,
            },
        },
        "filters": {
            "tg_msg_info": {"()": "monya.log.TgMsgInfoFilter"},
        },
    }

    return config


def setup_logging(service_config: ServiceConfig) -> None:
    config = get_config(service_config)
    logging.config.dictConfig(config)
