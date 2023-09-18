from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from facet import ServiceMixin
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .models import Chat, ChatUser, RoleEnum, User, UserDialog, UserSettings
from .settings import Settings


class Service(ServiceMixin):
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._engine = create_async_engine(self._dsn)
        self._sessionmaker = async_sessionmaker(self._engine, expire_on_commit=False)

    def get_alembic_config(self) -> Config:
        migrations_path = Path(__file__).parent / "migrations"

        config = Config()
        config.set_main_option("script_location", str(migrations_path))
        config.set_main_option("sqlalchemy.url", self._dsn)

        return config

    def migrate(self): 
        command.upgrade(self.get_alembic_config(), "head")

    def create_migration(self, message: str | None = None):
        command.revision(self.get_alembic_config(), message=message, autogenerate=True)

    async def get_user(self, id: int) -> User | None:
        async with self._sessionmaker() as session:
            return await session.get(User, id)

    async def add_new_user(self, id: int, full_name: str) -> User:
        user = User(telegram_id=id, full_name=full_name)
        user_settings = UserSettings(user=user)
        user_dialog = UserDialog(user=user)

        async with self._sessionmaker() as session:
            async with session.begin():
                session.add_all([user, user_settings, user_dialog])
            await session.refresh(user, attribute_names=["settings", "dialog"])
        return user

    async def get_or_create_user(self, id: int, full_name: str) -> User:
        return await self.get_user(id=id) or await self.add_new_user(id=id, full_name=full_name)

    async def get_chat(self, id: int) -> Chat | None:
        async with self._sessionmaker() as session:
            return await session.get(Chat, id)

    async def add_new_chat(self, id: int, owner: User) -> Chat:
        chat = Chat(telegram_id=id, owner=owner)

        async with self._sessionmaker() as session:
            async with session.begin():
                session.add(chat)
            await session.refresh(chat, attribute_names=["users"])
        return chat

    async def add_chat_user(
            self,
            chat: Chat,
            user: User,
            role: RoleEnum = RoleEnum.MEMBER,
    ) -> Chat:
        chat_user = ChatUser(role=role)
        chat_user.user = user
        chat.users.append(chat_user)

        async with self._sessionmaker() as session:
            async with session.begin():
                session.add(chat)
        return chat

    async def remove_chat_user(self, chat: Chat, user: User) -> Chat:
        async with self._sessionmaker() as session:
            async with session.begin():
                await session.execute(
                    delete(ChatUser).filter(
                        ChatUser.chat_id == chat.telegram_id,
                        ChatUser.user_id == user.telegram_id,
                    )
                )
        return chat

    async def set_chat_owner(self, chat: Chat, owner: User) -> Chat:
        old_owner = ChatUser(role=RoleEnum.MANAGER, user=chat.owner)

        async with self._sessionmaker() as session:
            async with session.begin():
                await session.execute(
                    delete(ChatUser).filter(
                        ChatUser.chat_id == chat.telegram_id,
                        ChatUser.user_id == owner.telegram_id,
                    )
                )
                chat.users.append(old_owner)
                chat.owner_id = owner.telegram_id
                session.add(chat)

        return chat

    async def can_manage_chat(self, chat: Chat, user: User) -> bool:
        if chat.owner_id == user.telegram_id:
            return True

        async with self._sessionmaker() as session:
            result = await session.execute(
                select(ChatUser).where(
                    ChatUser.role == RoleEnum.MANAGER,
                    ChatUser.user_id == user.telegram_id,
                ),
            )
            return result.first() is not None

    async def get_chat_managers(self, chat: Chat) -> list[User]:
        async with self._sessionmaker() as session:
            result = await session.execute(
                select(ChatUser).filter(
                    ChatUser.role == RoleEnum.MANAGER,
                    ChatUser.chat_id == chat.telegram_id,
                ),
            )
            return [chat_user.user for chat_user in result.scalars().unique().all()]

    async def set_dialog_state(self, user: User, state: str | None) -> User:
        user.dialog.state = state

        async with self._sessionmaker() as session:
            async with session.begin():
                session.add(user.dialog)
        return user

    async def get_dialog_state(self, user: User) -> str | None:
        return user.dialog.state

    async def set_dialog_data(self, user: User, data: dict[str, Any]) -> User:
        user.dialog.data = data

        async with self._sessionmaker() as session:
            async with session.begin():
                session.add(user.dialog)
        return user

    async def get_dialog_data(self, user: User) -> dict[str, Any]:
        return user.dialog.data


def get_service(settings: Settings) -> Service:
    return Service(dsn=str(settings.dsn))
