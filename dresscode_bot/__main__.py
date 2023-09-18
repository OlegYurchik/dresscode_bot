import logging

from .cli import get_cli


def setup_logging():
    logging.basicConfig(
        format="|%(asctime)-23s|%(levelname)-8s| %(message)s",
        level=logging.INFO,
    )


if __name__ == "__main__":
    setup_logging()

    cli = get_cli()    
    cli()
