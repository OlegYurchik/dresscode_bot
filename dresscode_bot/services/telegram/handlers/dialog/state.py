from aiogram.fsm.state import State, StatesGroup


class DialogState(StatesGroup):
    change_owner = State()
    add_manager = State()
