from pathlib import Path

from pydantic import PositiveInt, conint, model_validator
from pydantic_settings import BaseSettings

from .enums import BotMethodEnum


class WebhookSettings(BaseSettings):
    url: str
    secret: str | None = None
    path: str = "/"
    ssl_certificate: Path | None = None
    ssl_private_key: Path | None = None
    server_port: conint(gt=0, lt=65536) = 8443


class PollingSettings(BaseSettings):
    timeout: PositiveInt = 10


class Settings(BaseSettings):
    token: str
    method: BotMethodEnum = BotMethodEnum.POLLING
    webhook: WebhookSettings | None = None
    polling: PollingSettings = PollingSettings()

    @model_validator(mode="after")
    def model_validator(cls, values: "Settings"):
        if values.method == BotMethodEnum.WEBHOOK and values.webhook is None:
            raise ValueError("field 'method' with 'webhook' value must have a 'webhook' settings")

        return values
