import enum
from typing import Any, Optional

import sqlalchemy as sa
from pydantic import PositiveInt
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RoleEnum(str, enum.Enum):
    MANAGER = "manager"
    MEMBER = "member"


class LanguageEnum(str, enum.Enum):
    RUSSIAN = "russian"
    ENGLISH = "english"


class ChatUser(Base):
    __tablename__ = "chats_users"

    user_id: Mapped[int] = mapped_column(sa.ForeignKey("users.telegram_id"), primary_key=True)
    chat_id: Mapped[int] = mapped_column(sa.ForeignKey("chats.telegram_id"), primary_key=True)
    role: Mapped[RoleEnum] = mapped_column(nullable=False, default=RoleEnum.MEMBER)

    user: Mapped["User"] = relationship(back_populates="chats", lazy="joined")
    chat: Mapped["Chat"] = relationship(back_populates="users", lazy="joined")


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[PositiveInt] = mapped_column(primary_key=True)
    full_name: Mapped[str]

    chats: Mapped[list[ChatUser]] = relationship(back_populates="user", lazy="joined")
    ownership_chats: Mapped[list["Chat"]] = relationship(back_populates="owner", lazy="joined")
    settings: Mapped["UserSettings"] = relationship(back_populates="user", lazy="joined")
    dialog: Mapped["UserDialog"] = relationship(back_populates="user", lazy="joined")

    def __eq__(self, other: "User") -> bool:
        return self.telegram_id == other.telegram_id


class UserSettings(Base):
    __tablename__ = "users_settings"

    user_id: Mapped[int] = mapped_column(sa.ForeignKey("users.telegram_id"), primary_key=True)
    language: Mapped[Optional[LanguageEnum]]

    user: Mapped[User] = relationship(back_populates="settings", lazy="joined")


class UserDialog(Base):
    __tablename__ = "users_dialog"

    user_id: Mapped[int] = mapped_column(sa.ForeignKey("users.telegram_id"), primary_key=True)

    state: Mapped[Optional[str]]
    data: Mapped[dict[str, Any]] = mapped_column(type_=sa.JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="dialog", lazy="joined")


class Chat(Base):
    __tablename__ = "chats"

    telegram_id: Mapped[PositiveInt] = mapped_column(primary_key=True)
    owner_id: Mapped[PositiveInt] = mapped_column(sa.ForeignKey(f"{User.__tablename__}.telegram_id"))

    users: Mapped[list[ChatUser]] = relationship(back_populates="chat", lazy="joined")
    owner: Mapped[User] = relationship(back_populates="ownership_chats", lazy="joined")

    def __eq__(self, other: "Chat") -> bool:
        return self.telegram_id == other.telegram_id
