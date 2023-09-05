import logging
import ssl
import time
from pathlib import Path
from typing import Sequence

from aiogram import Bot, Dispatcher
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import ChatMemberUpdated, ChatPermissions
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from .enums import BotMethodEnum, ChatPermissionEnum


class DressCodeBot:
    def __init__(
            self,
            token: str,
            method: BotMethodEnum,
            whitelist: Sequence[int],
            permissions: Sequence[ChatPermissionEnum],
            polling_timeout: int = 10,
            webhook_url: str = "https://localhost",
            webhook_secret: str | None = None,
            webhook_path: str = "/",
            server_port: int = 8443,
            ssl_certificate: Path | None = None,
            ssl_private_key: Path | None = None,
    ):
        self._token = token
        self._method = method
        self._whitelist = set(whitelist)
        self._permissions = permissions
        self._polling_timeout = polling_timeout
        self._webhook_url = webhook_url
        self._webhook_secret = webhook_secret
        self._webhook_path = webhook_path
        self._server_port = server_port
        self._ssl_certificate = ssl_certificate
        self._ssl_private_key = ssl_private_key

        self._bot = Bot(token=self._token)
        self._dispatcher = Dispatcher()
        self._logger = logging.getLogger(__name__)

        self._dispatcher.chat_member.register(
            self._join_handler,
            ChatMemberUpdatedFilter(JOIN_TRANSITION),
        )

    def run(self):
        while True:
            try:
                self._run()
            except Exception:
                self._logger.exception("Got exception")
                time.sleep(1)

    def _run(self):
        if self._method == BotMethodEnum.POLLING:
            self._run_polling()
        elif self._method == BotMethodEnum.WEBHOOK:
            self._run_webhook()
        else:
            available_methods = ", ".join(f"'{method.value}'" for method in BotMethodEnum)
            raise ValueError(
                f"Incorrect method '{self._method}', must be one of ({available_methods})",
            )

    def _run_polling(self):
        self._logger.info("Start bot by polling")
        self._dispatcher.run_polling(
            self._bot,
            polling_timeout=self._polling_timeout,
        )

    def _run_webhook(self):
        self._logger.info("Start bot by webhook")
       
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
            self._logger.info("Load SSL certificate and private key")
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain(self._ssl_certificate, self._ssl_private_key)

        web.run_app(app, port=self._server_port, ssl_context=context)

    async def _webhook_on_startup(self, bot: Bot):
        url = f"{self._webhook_url}{self._webhook_path}"
        self._logger.info("Set webhook: %s", url)
        await bot.set_webhook(url, secret_token=self._webhook_secret)

    async def _webhook_on_shutdown(self, bot: Bot):
        self._logger.info("Delete webhook")
        await bot.delete_webhook()

    async def _join_handler(self, event: ChatMemberUpdated):
        chat = event.chat
        member = event.new_chat_member
        parameters = [
            chat.full_name,
            chat.id,
            member.user.full_name,
            member.user.id,
        ]
        if member.user.id in self._whitelist:
            self._logger.info(
                "[%s (%d)] Ignoring chat member: [%s (%d)]",
                *parameters,
            )
            return

        self._logger.info("[%s (%d)] Chat member joined: [%s (%d)]", *parameters)

        result = await self._bot.restrict_chat_member(
            chat_id=event.chat.id,
            user_id=member.user.id,
            permissions=ChatPermissions(**{
                permission.value: True
                for permission in self._permissions
            }),
        )
        if result:
            self._logger.info("[%s (%d)] Restrictions added: [%s (%d)]", *parameters)
        else:
            self._logger.error("[%s (%d)] Restrictions was not added: [%s (%d)]", *parameters)
