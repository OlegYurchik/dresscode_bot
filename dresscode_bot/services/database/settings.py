from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    dsn: AnyUrl = "sqlite+aiosqlite:///db.sqlite3"
