import logging
from typing import Any, Callable

from aiogram.types import Message, CallbackQuery


logger = logging.getLogger(__name__)


async def user_middleware(
        handler: Callable,
        event: Message | CallbackQuery,
        data: dict[str, Any],
) -> Any:
    if event.from_user is None:
        logger.error("Event have no 'from_user' field")
        return

    service = data["service"]
    user = await service.database.get_or_create_user(
        id=event.from_user.id,
        full_name=event.from_user.full_name,
    )
    data["user"] = user

    custom_logger = logging.getLogger("dialog")
    custom_handler = logging.StreamHandler()
    custom_formatter = logging.Formatter(
        fmt=(
            "|%(asctime)-23s|%(levelname)-8s| [%(handler)-16.16s]"
            "[%(user_telegram_id)-12.12s][%(user_full_name)-16.16s] %(message)s"
        ),
    )
    custom_handler.setFormatter(custom_formatter)
    custom_logger.addHandler(custom_handler)
    custom_logger = logging.LoggerAdapter(custom_logger, extra={
        "user_full_name": user.full_name,
        "user_telegram_id": user.telegram_id,
        "handler": handler.__wrapped__.__self__.callback.__name__,
    })
    data["logger"] = custom_logger

    return await handler(event, data)
