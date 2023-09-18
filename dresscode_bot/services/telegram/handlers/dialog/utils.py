from typing import Any, Sequence, Type

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .callback_data import PaginationCallbackData


def inline_keyboard_pagination(
        elements: Sequence[InlineKeyboardButton],
        page: int,
        page_count: int,
        callback_type: Type[PaginationCallbackData],
        callback_extra_args: dict[str, Any] | None = None,
        columns: int = 1,
        back_callback: CallbackData | None = None,
        add_callback: CallbackData | None = None,
) -> InlineKeyboardMarkup:
    callback_extra_args = callback_extra_args or {}
    keyboard = [list(elements[i:i + columns]) for i in range(0, len(elements), columns)]
    if add_callback is not None:
        keyboard.insert(0, [InlineKeyboardButton(text="Добавить", callback_data=add_callback.pack())])
    pagination_row = [InlineKeyboardButton(
        text=str(page),
        callback_data=callback_type(**callback_extra_args, page=page).pack(),
    )]
    if page > 1:
        pagination_row.insert(
            0,
            InlineKeyboardButton(
                text=f"< {page - 1}",
                callback_data=callback_type(**callback_extra_args, page=page - 1).pack(),
            ),
        )
    if page < page_count:
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{page + 1} >",
                callback_data=callback_type(**callback_extra_args, page=page + 1).pack(),
            ),
        )
    if len(pagination_row) > 1:
        keyboard.append(pagination_row)
    if back_callback is not None:
        keyboard.append([InlineKeyboardButton(text="Назад", callback_data=back_callback.pack())])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def generate_full_name(first_name: str | None, last_name: str | None) -> str:
    first_name = first_name or ""
    last_name = last_name or ""
    return f"{first_name} {last_name}".strip()
