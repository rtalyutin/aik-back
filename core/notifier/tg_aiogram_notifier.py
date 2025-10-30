import logging
from typing import Optional
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.notifier.notifier import Notifier
from core.notifier.telegram_notifable import TelegramNotifiable

logger = logging.getLogger(__name__)


class TgAiogramNotifier(Notifier):
    def __init__(
        self,
        bot_token: str,
        channel_id: int | str,
    ):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.client: Optional[Bot] = None

        self.client = Bot(
            token=self.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    async def send_error_notification(
        self,
        error: Exception,
        context: str = "",
    ) -> None:
        if not isinstance(error, TelegramNotifiable):
            return

        await self.send(error.get_notification_message())

    async def send(self, message: str):
        try:
            if len(message) > 4000:
                message = message[:4000] + "\n\n..."

            await self.client.send_message(
                self.channel_id,
                message,
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    async def send_notification(
        self,
        message: str,
    ) -> None:
        await self.send(message)
