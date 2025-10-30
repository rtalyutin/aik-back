from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config import get_config

config = get_config()

SessionFactory = None
if config.POSTGRES_DSN is not None:
    engine = create_async_engine(str(config.POSTGRES_DSN), echo=config.DEBUG)
    SessionFactory = async_sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
