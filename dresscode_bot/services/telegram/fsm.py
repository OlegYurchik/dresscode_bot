from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseEventIsolation, BaseStorage, StateType, StorageKey

from dresscode_bot.services import database
from dresscode_bot.services.database.models import User


class DatabaseStorage(BaseStorage):
    def __init__(self, database_service: database.Service):
        self._database_service = database_service

    async def get_user_by_key(self, key: StorageKey) -> User | None:
        return await self._database_service.get_user(id=key.user_id)

    async def set_state(self, key: StorageKey, state: StateType | None = None):
        user = await self.get_user_by_key(key=key)
        if user is None:
            return

        if isinstance(state, State):
            state = state.state
        await self._database_service.set_dialog_state(user=user, state=state)

    async def get_state(self, key: StorageKey) -> str | None:
        user = await self.get_user_by_key(key=key)
        if user is None:
            return

        return await self._database_service.get_dialog_state(user=user)

    async def set_data(self, key: StorageKey, data: dict[str, Any]):
        user = await self.get_user_by_key(key=key)
        if user is None:
            return

        await self._database_service.set_dialog_data(user=user, data=data)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        user = await self.get_user_by_key(key=key)
        if user is None:
            return {}

        return await self._database_service.get_dialog_data(user=user)

    async def close(self):
        pass


class DatabaseEventIsolation(BaseEventIsolation):
    @asynccontextmanager
    async def lock(self, key: StorageKey) -> AsyncGenerator[None, None]:
        pass

    async def close(self):
        pass
