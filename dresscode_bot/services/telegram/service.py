import logging
import ssl
from pathlib import Path
from typing import Any, Callable

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters.chat_member_updated import (
    ChatMemberUpdatedFilter,
    JOIN_TRANSITION,
    PROMOTED_TRANSITION,
)
from aiogram.methods import delete_webhook
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from facet import ServiceMixin

from dresscode_bot.services import database
from dresscode_bot.services.database.models import Chat
from .enums import BotMethodEnum
from .fsm import DatabaseStorage
from .handlers import dialog, new_chat, new_member
from .settings import Settings


logger = logging.getLogger(__name__)



class Service(ServiceMixin):
    def __init__(
            self,
            database_service: database.Service,
            token: str,
            method: BotMethodEnum,
            polling_timeout: int = 10,
            webhook_url: str = "https://localhost",
            webhook_secret: str | None = None,
            webhook_path: str = "/",
            server_port: int = 8443,
            ssl_certificate: Path | None = None,
            ssl_private_key: Path | None = None,
    ):
        self._database_service = database_service
        self._token = token
        self._method = method
        self._polling_timeout = polling_timeout
        self._webhook_url = webhook_url
        self._webhook_secret = webhook_secret
        self._webhook_path = webhook_path
        self._server_port = server_port
        self._ssl_certificate = ssl_certificate
        self._ssl_private_key = ssl_private_key
        self._me_id = None

        self._bot = Bot(token=self._token)
        self._dispatcher = Dispatcher(
            storage=DatabaseStorage(database_service=self._database_service),
        )
        if self._method == BotMethodEnum.POLLING:
            self._background_task = self._polling
        elif self._method == BotMethodEnum.WEBHOOK:
            self._background_task = self._webhook
        else:
            available_methods = ", ".join(f"'{method.value}'" for method in BotMethodEnum)
            raise ValueError(
                f"Incorrect method '{self._method}', must be one of ({available_methods})",
            )

        self.setup_dispatcher()

    @property
    def database(self) -> database.Service:
        return self._database_service

    @property
    def me_id(self) -> int | None:
        return self._me_id

    @property
    def bot(self) -> Bot:
        return self._bot

    @property
    def dependencies(self) -> list[ServiceMixin]:
        return [
            self._database_service,
        ]

    async def service_middleware(
            self,
            handler: Callable,
            event: Update,
            data: dict[str, Any],
    ) -> Any:
        data["service"] = self
        return await handler(event, data)

    def setup_dispatcher(self):
        self._dispatcher.update.middleware()(self.service_middleware)

        self._dispatcher.my_chat_member.register(
            new_chat.new_chat_handler,
            F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]),
            ChatMemberUpdatedFilter(PROMOTED_TRANSITION),
        )
        self._dispatcher.chat_member.register(
            new_member.new_member_handler,
            F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]),
            ChatMemberUpdatedFilter(JOIN_TRANSITION),
        )
        self._dispatcher.include_router(dialog.router)

    async def start(self):
        logger.info("[telegram] Start service")

        me = await self._bot.me()
        self._me_id = me.id

        self.add_task(self._background_task())

    async def _polling(self):
        logger.info("[telegram] Start bot")

        await self._bot.delete_webhook()
        await self._dispatcher.start_polling(
            self._bot,
            polling_timeout=self._polling_timeout,
            handle_signals=False,
        )

    async def _webhook(self):
        logger.info("[telegram] Start bot")

        self._dispatcher.startup.register(self._webhook_on_startup)
        self._dispatcher.shutdown.register(self._webhook_on_shutdown)

        app = web.Application()
        request_handler = SimpleRequestHandler(
            dispatcher=self._dispatcher,
            bot=self._bot,
            secret_token=self._webhook_secret,
        )
        request_handler.register(app, path=self._webhook_path)
        setup_application(app, self._dispatcher, bot=self._bot)

        context = None
        if self._ssl_certificate and self._ssl_private_key:
            logger.info("[telegram] Load SSL certificate and private key")
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain(self._ssl_certificate, self._ssl_private_key)

        await web._run_app(app, port=self._server_port, ssl_context=context)

    async def _webhook_on_startup(self, bot: Bot):
        url = f"{self._webhook_url}{self._webhook_path}"
        logger.info("[telegram] Set webhook: %s", url)

        await bot.set_webhook(url, secret_token=self._webhook_secret)

    async def _webhook_on_shutdown(self, bot: Bot):
        logger.info("[telegram] Delete webhook")

        await bot.delete_webhook()

    async def get_chat(self, id: int) -> Chat | None:
        chat = await self._database_service.get_chat(id=id)
     
        if chat is not None:
            return chat

        admins = await self._bot.get_chat_administrators(chat_id=id)
        in_admins, owner = False, None
        for admin in admins:
            if admin.user.id == self._me_id:
                in_admins = True
            if admin.status == ChatMemberStatus.CREATOR:
                owner = admin.user

            if not in_admins or not owner:
                continue

            owner = await self._database_service.get_or_create_user(
                id=owner.id,
                full_name=owner.full_name,
            )
            return await self._database_service.add_new_chat(id=id, owner=owner)


def get_service(database_service: database.Service, settings: Settings) -> Service:
    parameters = {
        "database_service": database_service,
        "token": settings.token,
        "method": settings.method,
    }
    if settings.polling is not None:
        parameters.update({
            "polling_timeout": settings.polling.timeout,
        })
    if settings.webhook is not None:
        parameters.update({
            "webhook_url": settings.webhook.url,
            "webhook_path": settings.webhook.path,
            "webhook_secret": settings.webhook.secret,
            "server_port": settings.webhook.server_port,
        })
    
    return Service(**parameters)
