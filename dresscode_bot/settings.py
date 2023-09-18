from pathlib import Path

import yaml
from pydantic_settings import BaseSettings

from .services import database, telegram


class Settings(BaseSettings):
    database: database.Settings
    telegram: telegram.Settings


def get_settings(config_path: Path | None = None) -> Settings:
    settings_parameters = {}
    if config_path is not None:
        with open(config_path) as config_file:
            settings_parameters = yaml.safe_load(config_file)
    
    return Settings(**settings_parameters)
