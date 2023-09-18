import logging

from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated

from dresscode_bot.services.database.models import User


logger = logging.getLogger(__name__)


async def new_chat_handler(event: ChatMemberUpdated, service, user: User):
    parameters = [
        event.chat.full_name,
        event.chat.id,
        event.new_chat_member.user.full_name,
        event.new_chat_member.user.id,
    ]

    if service.me_id != event.new_chat_member.user.id:
        logger.error("[%s (%d)] Incorrect user: [%s (%d)]", *parameters)
        return
    if event.new_chat_member.status != ChatMemberStatus.ADMINISTRATOR:
        logger.error(
            "[%s (%d)] Incorrect user role: %s",
            *parameters[:2], event.new_chat_member.status,
        )

    chat = await service.get_chat(id=event.chat.id)
    if chat is not None:
        logger.warning("[%s (%d)] Chat already exists", *parameters[:2])
        return

    await service.database.create_chat(id=event.chat.id, owner=user)
    logger.info("[%s (%d)] New chat added")
