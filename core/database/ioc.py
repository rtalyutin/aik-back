from typing import AsyncGenerator, Self

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from core.database.uow import UoW
from config import get_config
from core.database.db import SessionFactory


class DatabaseDepsProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def get_uow(self: Self) -> AsyncGenerator[UoW, None]:
        config = get_config()
        if config.POSTGRES_DSN is None:
            return

        async with SessionFactory() as session:
            yield UoW(session)

    @provide(scope=Scope.APP)
    async def get_session_factory(
        self,
    ) -> AsyncGenerator[async_sessionmaker[AsyncSession]]:
        config = get_config()
        if config.POSTGRES_DSN is None:
            return

        yield SessionFactory
