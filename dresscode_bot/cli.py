import argparse
from pathlib import Path


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        "DressCode Bot",
        description="Telegram bot to manage user rights",
    )

    parser.add_argument(
        "-c", "--config",
        dest="config_path",
        type=Path,
        help="Path to configuration file",
    )

    return parser
