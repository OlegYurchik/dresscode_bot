from pathlib import Path
from typing import Optional

import typer

from .services import database, telegram
from .settings import get_settings


def config_callback(
        ctx: typer.Context,
        config_path: Optional[Path] = typer.Option(
            None,
            "-c", "--config",
            help="Path for configuration JSON file",
        ),
):
    ctx.obj = ctx.obj or {}
    ctx.obj["settings"] = get_settings(config_path=config_path)


def get_cli() -> typer.Typer:
    cli = typer.Typer(
        name="DressCode Bot",
    )

    cli.callback()(config_callback)
    cli.add_typer(database.get_cli(), name="database")
    cli.add_typer(telegram.get_cli(), name="telegram")

    return cli
