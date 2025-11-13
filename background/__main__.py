import asyncio
import logging
import signal
from typing import List

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from application.karaoke_tracks.services.lalal_client import ILalalClient
from application.karaoke_tracks.services.assemblyai_client import IAssemblyAIClient
from background.karaoke_tasks import (
    process_karaoke_track_splitting_init,
    process_karaoke_track_splitting_send,
    process_karaoke_track_splitting_results,
    process_karaoke_transcription_init,
    process_karaoke_transcription_send,
    process_karaoke_transcription_results,
    process_karaoke_subtitles_init,
    process_karaoke_subtitles_results,
    process_karaoke_final_track_creation,
)

from config import get_config

from core import ioc
from core.file_storage.file_storage_service import FileStorageService
from core.notifier.notifier import Notifier
from logger import setup_logging

container = ioc.make_ioc(with_fast_api=False)

config = get_config()
setup_logging(config, service_name="background")
logger = logging.getLogger(__name__)


async def _graceful_shutdown(tasks: List[asyncio.Task]):
    logger.info("Initiating graceful shutdown", extra={"tasks_count": len(tasks)})
    for task in tasks:
        if not task.done():
            task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Graceful shutdown completed")


async def main():
    shutdown_initiated = False

    notifier: Notifier = await container.get(Notifier)

    def signal_handler():
        nonlocal shutdown_initiated
        if not shutdown_initiated:
            logger.info("Received shutdown signal")
            shutdown_initiated = True
            asyncio.create_task(_graceful_shutdown(tasks))

    session_maker: async_sessionmaker[AsyncSession] = await container.get(
        async_sessionmaker[AsyncSession]
    )

    # Получаем сервисы для karaoke tracks
    lalal_client: ILalalClient = await container.get(ILalalClient)
    assemblyai_client: IAssemblyAIClient = await container.get(IAssemblyAIClient)
    file_storage_service = await container.get(FileStorageService)

    tasks = [
        # Задачи karaoke tracks - splitting
        asyncio.create_task(
            process_karaoke_track_splitting_init(session_maker, notifier)
        ),
        asyncio.create_task(
            process_karaoke_track_splitting_send(
                session_maker, lalal_client, file_storage_service, notifier
            )
        ),
        asyncio.create_task(
            process_karaoke_track_splitting_results(
                session_maker, lalal_client, file_storage_service, notifier
            )
        ),
        # Задачи karaoke tracks - transcription
        asyncio.create_task(
            process_karaoke_transcription_init(session_maker, notifier)
        ),
        asyncio.create_task(
            process_karaoke_transcription_send(
                session_maker, assemblyai_client, file_storage_service, notifier
            )
        ),
        asyncio.create_task(
            process_karaoke_transcription_results(
                session_maker, assemblyai_client, file_storage_service, notifier
            )
        ),
        asyncio.create_task(process_karaoke_subtitles_init(session_maker, notifier)),
        asyncio.create_task(
            process_karaoke_subtitles_results(
                session_maker, assemblyai_client, notifier
            )
        ),
        asyncio.create_task(
            process_karaoke_final_track_creation(session_maker, notifier)
        ),
    ]

    loop = asyncio.get_running_loop()
    for sig in [signal.SIGTERM, signal.SIGINT]:
        loop.add_signal_handler(sig, signal_handler)

    logger.info("Background tasks started", extra={"tasks_count": len(tasks)})

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        if not shutdown_initiated:
            await _graceful_shutdown(tasks)


if __name__ == "__main__":
    asyncio.run(main())
