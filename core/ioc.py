from typing import List, Self

from dishka import make_async_container, AsyncContainer, Provider, provide, Scope
from dishka.integrations.fastapi import FastapiProvider

from application.karaoke_tracks.ioc import KaraokeTracksDepsProvider
from config import get_config
from core.database.ioc import DatabaseDepsProvider
from core.auth.ioc import AuthDepsProvider
from core.file_storage.ioc import FileStorageDepsProvider
from core.notifier.notifier import Notifier
from core.notifier.tg_aiogram_notifier import TgAiogramNotifier


class CoreDepsProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_notifier_app(self: Self) -> Notifier:
        config = get_config()
        tg_notifier = TgAiogramNotifier(
            bot_token=config.TG_BOT_TOKEN,
            channel_id=config.TG_CHANNEL_ID,
        )

        return tg_notifier


def make_ioc(with_fast_api: bool = False) -> AsyncContainer:
    providers: List[Provider] = [
        DatabaseDepsProvider(),
        KaraokeTracksDepsProvider(),
        FileStorageDepsProvider(),
        CoreDepsProvider(),
    ]
    if with_fast_api:
        providers.append(AuthDepsProvider())
        providers.append(FastapiProvider())

    return make_async_container(*providers)
