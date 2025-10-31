from typing import Self

from dishka import Provider, Scope, provide

from application.karaoke_tracks.services.lalal_client import ILalalClient, LalalClient
from application.karaoke_tracks.services.assemblyai_client import (
    IAssemblyAIClient,
    AssemblyAIClient,
)
from config import get_config


class KaraokeTracksDepsProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_lalal_client(self: Self) -> ILalalClient:
        config = get_config()
        return LalalClient(api_key=config.LALAL_AI_API_KEY)

    @provide(scope=Scope.APP)
    async def get_assemblyai_client(self: Self) -> IAssemblyAIClient:
        config = get_config()
        return AssemblyAIClient(api_key=config.ASSEMBLY_AI_API_KEY)
