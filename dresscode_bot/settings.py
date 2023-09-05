from pathlib import Path
from pydantic import PositiveInt, conint
from pydantic_settings import BaseSettings

from .enums import BotMethodEnum, ChatPermissionEnum


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
    polling: PollingSettings | None = None

    whitelist: list[PositiveInt]
    permissions: list[ChatPermissionEnum] = []
