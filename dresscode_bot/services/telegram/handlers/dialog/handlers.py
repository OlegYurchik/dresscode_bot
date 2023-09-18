import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from dresscode_bot.services.database.models import Chat, RoleEnum, User
from .callback_data import (
    GroupCallbackData,
    GroupChangeOwnerCallbackData,
    GroupFunctionsCallbackData,
    GroupManagerAddCallbackData,
    GroupManagerCallbackData,
    GroupManagerRemoveCallbackData,
    GroupManagersCallbackData,
    GroupsCallbackData,
)
from .middlewares import user_middleware
from .state import DialogState
from .utils import generate_full_name, inline_keyboard_pagination


router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.message.middleware(user_middleware)
router.callback_query.middleware(user_middleware)


async def generate_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="Мои группы")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


@router.message(CommandStart())
@router.message(Command("menu"))
async def menu(message: Message, state: FSMContext, service, user: User, logger: logging.Logger):
    keyboard = await generate_menu_keyboard()
    await message.reply(text="Меню", reply_markup=keyboard)

    await state.set_state(None)
    await state.set_data({})


async def generate_groups_keyboard(
        service,
        user: User,
        page: int,
) -> InlineKeyboardMarkup | None:
    limit = 4
    groups = user.ownership_chats + user.chats
    page_count = len(groups) // limit + int(bool(len(groups) % limit))
    groups = groups[(page - 1) * limit:page * limit]
    if not groups:
        return

    groups = [await service.bot.get_chat(group.telegram_id) for group in groups]
    buttons = [
        InlineKeyboardButton(
            text=group.full_name,
            callback_data=GroupCallbackData(group_id=group.id).pack(),
        )
        for group in groups
    ]
    return inline_keyboard_pagination(
        elements=buttons,
        page=page,
        page_count=page_count,
        callback_type=GroupsCallbackData,
    )


@router.message(F.text == "Мои группы")
async def groups_message_handler(
        message: Message,
        state: FSMContext,
        service,
        user: User,
        logger: logging.Logger,
):
    keyboard = await generate_groups_keyboard(service=service, user=user, page=1)
    if keyboard is None:
        await message.reply(text="У Вас нет групп")
    else:
        await message.reply(text="Мои группы", reply_markup=keyboard)

    await state.set_state(None)
    await state.set_data({})


@router.callback_query(GroupsCallbackData.filter())
async def groups_callback_handler(
        callback: CallbackQuery,
        callback_data: GroupsCallbackData,
        state: FSMContext,
        service,
        user: User,
        logger: logging.Logger,
):
    if callback.message is None:
        logger.error("Field 'message' is None")
        return

    keyboard = await generate_groups_keyboard(service=service, user=user, page=callback_data.page)
    if keyboard is None:
        await callback.answer(text="У Вас нет групп", alert=True)
    else:
        await callback.message.edit_text(text="Группы")
        await callback.message.edit_reply_markup(reply_markup=keyboard)

    await state.set_state(None)
    await state.set_data({})


async def generate_group_keyboard(chat: Chat, user: User) -> InlineKeyboardMarkup:
    if chat.owner_id == user.telegram_id:
        keyboard = [
            [InlineKeyboardButton(
                text="Сменить владельца",
                callback_data=GroupChangeOwnerCallbackData(group_id=chat.telegram_id).pack(),
            )],
            [InlineKeyboardButton(
                text="Менеджеры",
                callback_data=GroupManagersCallbackData(group_id=chat.telegram_id).pack(),
            )],
        ]
    else:
        keyboard = []
    keyboard.extend([
        [InlineKeyboardButton(
            text="Функции",
            callback_data=GroupFunctionsCallbackData(group_id=chat.telegram_id).pack(),
        )],
        [InlineKeyboardButton(
            text="Назад",
            callback_data=GroupsCallbackData(page=1).pack(),
        )],
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(GroupCallbackData.filter())
async def group(
        callback: CallbackQuery,
        callback_data: GroupCallbackData,
        state: FSMContext,
        service,
        user: User,
        logger: logging.Logger,
):
    if callback.message is None:
        logger.error("Field 'message' is None")
        return

    chat = await service.get_chat(id=callback_data.group_id)
    if chat is None:
        logger.error("Have no chat: %d", callback_data.group_id)
        return
    if not await service.database.can_manage_chat(chat=chat, user=user):
        logger.error("Have no access to chat: %d", chat.telegram_id)
        return

    keyboard = await generate_group_keyboard(chat=chat, user=user)
    await callback.message.edit_text(text="Группа")
    await callback.message.edit_reply_markup(reply_markup=keyboard)

    await state.set_state(None)
    await state.set_data({})


@router.callback_query(GroupChangeOwnerCallbackData.filter())
async def change_group_owner(
        callback: CallbackQuery,
        callback_data: GroupChangeOwnerCallbackData,
        state: FSMContext,
        service,
        user: User,
        logger: logging.Logger,
):
    if callback.message is None:
        logger.error("Field 'message' is None")
        return

    chat = await service.get_chat(id=callback_data.group_id)
    if chat is None:
        logger.error("Have no chat: %d", callback_data.group_id)
        return
    if chat.owner_id != user.telegram_id:
        logger.error("Have no access to chat: %d", chat.telegram_id)
        return

    await callback.message.edit_text(
        text=(
            "Перешлите любое сообщение или отправьте контакт человека, которому хотите передать "
            "права управления"
        ),
    )

    await state.set_state(DialogState.change_owner)
    await state.set_data({"chat_id": chat.telegram_id})


@router.message(DialogState.change_owner)
async def change_group_owner_handler(
        message: Message,
        state: FSMContext,
        service,
        user: User,
        logger: logging.Logger,
):
    if not message.contact and not message.forward_from and not message.forward_sender_name:
        await message.reply(
            text=(
                "Перешлите любое сообщение или отправьте контакт человека, которому хотите "
                "передать права управления"
            ),
        )
        return

    data = await state.get_data()
    chat_id = data.get("chat_id")

    chat = await service.get_chat(id=chat_id)
    if chat is None:
        logger.error("Have no chat: %d", chat_id)
        return
    if chat.owner_id != user.telegram_id:
        logger.error("Have no access to chat: %d", chat.telegram_id)
        return

    if message.contact is not None:
        new_owner = await service.database.get_or_create_user(
            id=message.contact.user_id,
            full_name=generate_full_name(message.contact.first_name, message.contact.last_name),
        )
    elif message.forward_from is not None:
        new_owner = await service.database.get_or_create_user(
            id=message.forward_from.id,
            full_name=message.forward_from.full_name,
        )
    else:
        await message.reply(
            text="Этот пользователь закрыл свои данные, его нельзя сделать управляющим",
        )
        return

    await service.database.set_chat_owner(chat=chat, owner=new_owner)

    keyboard = await generate_group_keyboard(chat=chat, user=user)
    await message.answer(text="Меню группы", reply_markup=keyboard)

    await state.set_state(None)
    await state.set_data({})


async def generate_group_managers_keyboard(service, chat: Chat, page: int) -> InlineKeyboardMarkup:
    limit = 4
    managers = await service.database.get_chat_managers(chat=chat)
    page_count = len(managers) // limit + int(bool(len(managers) % limit))
    managers = managers[(page - 1) * limit:page * limit]

    buttons = [
        InlineKeyboardButton(
            text=manager.full_name,
            callback_data=GroupManagerCallbackData(
                group_id=chat.telegram_id,
                manager_id=manager.telegram_id,
            ).pack(),
        )
        for manager in managers
    ]
    return inline_keyboard_pagination(
        elements=buttons,
        page=page,
        page_count=page_count,
        callback_type=GroupManagersCallbackData,
        callback_extra_args={"group_id": chat.telegram_id},
        back_callback=GroupCallbackData(group_id=chat.telegram_id),
        add_callback=GroupManagerAddCallbackData(group_id=chat.telegram_id),
    )


@router.callback_query(GroupManagersCallbackData.filter())
async def group_managers(
        callback: CallbackQuery,
        callback_data: GroupManagersCallbackData,
        state: FSMContext,
        service,
        user: User,
        logger: logging.Logger,
):
    if callback.message is None:
        logger.error("Field 'message' is None")
        return

    chat = await service.get_chat(id=callback_data.group_id)
    if chat is None:
        logger.error("Have no chat: %d", callback_data.group_id)
        return

    if chat.owner_id != user.telegram_id:
        logger.error("Have no access to chat: %d", chat.telegram_id)
        return

    keyboard = await generate_group_managers_keyboard(service=service, chat=chat, page=1)
    await callback.message.edit_text(text="Менеджеры")
    await callback.message.edit_reply_markup(reply_markup=keyboard)

    await state.set_state(None)
    await state.set_data({})


@router.callback_query(GroupManagerAddCallbackData.filter())
async def group_add_manager(
        callback: CallbackQuery,
        callback_data: GroupManagerAddCallbackData,
        state: FSMContext,
        service,
        user: User,
        logger: logging.Logger,
):
    if callback.message is None:
        logger.error("Field 'message' is None")
        return

    chat = await service.get_chat(id=callback_data.group_id)
    if chat is None:
        logger.error("Have no chat: %d", callback_data.group_id)
        return

    if chat.owner_id != user.telegram_id:
        logger.error("Have no access to chat: %d", chat.telegram_id)
        return

    await callback.message.edit_text(
        text=(
            "Перешлите любое сообщение или отправьте контакт человека, которого хотите сделать "
            "менеджером"
        ),
    )

    await state.set_state(DialogState.add_manager)
    await state.set_data({"chat_id": chat.telegram_id})


@router.message(DialogState.add_manager)
async def group_add_manager_handler(
        message: Message,
        state: FSMContext,
        service,
        user: User,
        logger: logging.Logger,
):
    if not message.contact and not message.forward_from and not message.forward_sender_name:
        await message.reply(
            text=(
                "Перешлите любое сообщение или отправьте контакт человека, которого хотите сделать "
                "менеджером"
            ),
        )
        return

    data = await state.get_data()
    chat_id = data.get("chat_id")

    chat = await service.get_chat(id=chat_id)
    if chat is None:
        logger.error("Have no chat: %d", chat_id)
        return

    if chat.owner_id != user.telegram_id:
        logger.error("Have no access to chat: %d", chat.telegram_id)
        return

    if message.contact is not None:
        new_manager = await service.database.get_or_create_user(
            id=message.contact.user_id,
            full_name=generate_full_name(message.contact.first_name, message.contact.last_name),
        )
    elif message.forward_from is not None:
        new_manager = await service.database.get_or_create_user(
            id=message.forward_from.id,
            full_name=message.forward_from.full_name,
        )
    else:
        await message.reply(
            text="Этот пользователь скрыл свои данные, его нельзя сделать менеджером",
        )
        return

    await service.database.add_chat_user(chat=chat, user=new_manager, role=RoleEnum.MANAGER)

    keyboard = await generate_group_managers_keyboard(service=service, chat=chat, page=1)
    await message.reply(text=f"Менеджеры группы", reply_markup=keyboard)

    await state.set_state(None)
    await state.set_data({})


async def generate_group_manager_keyboard(chat: Chat, manager: User, back_callback: CallbackData):
    keyboard = [
        [InlineKeyboardButton(
            text="Удалить",
            callback_data=GroupManagerRemoveCallbackData(
                group_id=chat.telegram_id,
                manager_id=manager.telegram_id,
            ).pack(),
        )],
        [InlineKeyboardButton(
            text="Назад",
            callback_data=back_callback.pack(),
        )],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(GroupManagerCallbackData.filter())
async def group_manager(
        callback: CallbackQuery,
        callback_data: GroupManagerCallbackData,
        state: FSMContext,
        service,
        user: User,
        logger: logging.Logger,
):
    if callback.message is None:
        logger.error("Field 'message' is None")
        return

    chat = await service.get_chat(id=callback_data.group_id)
    if chat is None:
        logger.error("Have no chat: %d", callback_data.group_id)
        return

    if chat.owner_id != user.telegram_id:
        logger.error("Have no access to chat: %d", chat.telegram_id)
        return

    manager = await service.database.get_user(id=callback_data.manager_id)
    if manager is None:
        logger.error("Have no user: %d", callback_data.manager_id)
        return

    keyboard = await generate_group_manager_keyboard(
        chat=chat,
        manager=manager,
        back_callback=GroupManagerCallbackData(
            group_id=chat.telegram_id,
            manager_id=manager.telegram_id,
        ),
    )
    await callback.message.edit_text(text=f"Менеджер {manager.full_name}")
    await callback.message.edit_reply_markup(reply_markup=keyboard)

    await state.set_state(None)
    await state.set_data({})


@router.callback_query(GroupManagerRemoveCallbackData.filter())
async def group_manager_remove(
        callback: CallbackQuery,
        callback_data: GroupManagerRemoveCallbackData,
        state: FSMContext,
        service,
        user: User,
        logger: logging.Logger,
):
    if callback.message is None:
        logger.error("Field 'message' is None")
        return

    chat = await service.get_chat(id=callback_data.group_id)
    if chat is None:
        logger.error("Have no chat: %d", callback_data.group_id)
        return

    if chat.owner_id != user.telegram_id:
        logger.error("Have no access to chat: %d", chat.telegram_id)
        return

    manager = await service.database.get_user(id=callback_data.manager_id)
    if manager is None:
        logger.error("Have no user: %d", callback_data.manager_id)
        return

    await service.database.remove_chat_user(chat=chat, user=manager)

    keyboard = await generate_group_managers_keyboard(service=service, chat=chat, page=1)
    await callback.message.edit_text(text="Меню группы")
    await callback.message.edit_reply_markup(reply_markup=keyboard)

    await state.set_state(None)
    await state.set_data({})


@router.callback_query(GroupFunctionsCallbackData.filter())
async def group_functions(callback: CallbackQuery):
    await callback.answer(text="Ещё не реализовано", alert=True)
