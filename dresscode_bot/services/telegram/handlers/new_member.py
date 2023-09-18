import logging

from aiogram.types import ChatMemberUpdated, ChatPermissions


logger = logging.getLogger(__name__)


async def new_member_handler(event: ChatMemberUpdated, service):
    parameters = [
        event.chat.full_name,
        event.chat.id,
        event.new_chat_member.user.full_name,
        event.new_chat_member.user.id,
    ]

    chat = await service.get_chat(id=event.chat.id)
    if chat is None:
        logger.info("[%s (%d)] Inactive chat", *parameters[:2])
        return

    logger.info("[%s (%d)] Chat member joined: [%s (%d)]", *parameters)
    result = await service.bot.restrict_chat_member(
        chat_id=event.chat.id,
        user_id=event.new_chat_member.user.id,
        permissions=ChatPermissions(),
    )
    if result:
        logger.info("[%s (%d)] Restrictions added: [%s (%d)]", *parameters)
    else:
        logger.error("[%s (%d)] Restrictions was not added: [%s (%d)]", *parameters)
