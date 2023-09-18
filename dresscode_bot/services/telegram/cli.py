import asyncio
import typer

from dresscode_bot.services import database
from .service import Service, get_service


def service_callback(ctx: typer.Context):
    settings = ctx.obj["settings"]
    database_service = database.get_service(settings=settings.database)
    telegram_service = get_service(database_service=database_service, settings=settings.telegram)

    ctx.obj["database"] = database_service
    ctx.obj["telegram"] = telegram_service


def run(ctx: typer.Context):
    telegram_service: Service = ctx.obj["telegram"]

    asyncio.run(telegram_service.run())


def get_cli() -> typer.Typer:
    cli = typer.Typer(name="Telegram Bot")

    cli.callback()(service_callback)
    cli.command(name="run")(run)

    return cli
