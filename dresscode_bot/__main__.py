import json
import logging.config

from .bot import DressCodeBot
from .cli import get_parser
from .settings import Settings


def setup_logging():
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)-8s %(message)s"
            },
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": True,
            },
        },
    })

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    setup_logging()

    settings_parameters = {}
    if args.config_path is not None:
        with open(args.config_path) as config_file:
            settings_parameters = json.load(config_file)
    settings = Settings(**settings_parameters)

    parameters = {
        "token": settings.token,
        "method": settings.method,
        "whitelist": settings.whitelist,
        "permissions": settings.permissions,
    }
    if settings.polling is not None:
        parameters.update({
            "polling_timeout": settings.polling.timeout,
        })
    if settings.webhook is not None:
        parameters.update({
            "webhook_url": settings.webhook.url,
            "webhook_path": settings.webhook.path,
            "webhook_secret": settings.webhook.secret,
            "server_port": settings.webhook.server_port,
        })
    dresscode_bot = DressCodeBot(**parameters)

    dresscode_bot.run()
