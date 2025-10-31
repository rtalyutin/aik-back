import asyncio
import logging
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from application.karaoke_tracks.use_cases.process_track_splitting import (
    process_track_splitting,
)
from application.karaoke_tracks.use_cases.process_transcription import (
    process_transcription,
)
from application.karaoke_tracks.services.lalal_client import ILalalClient
from application.karaoke_tracks.services.assemblyai_client import IAssemblyAIClient
from core.file_storage.file_storage_service import FileStorageService
from core.notifier.notifier import Notifier

logger = logging.getLogger(__name__)


async def process_karaoke_track_splitting(
    session_maker: async_sessionmaker[AsyncSession],
    lalal_client: ILalalClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
):
    """Фоновая задача для обработки разделения треков"""
    iteration = 0
    task_name = "process_karaoke_track_splitting"

    while True:
        iteration += 1
        logger.info(
            "Processing karaoke track splitting",
            extra={"task": task_name, "iteration": iteration},
        )

        task = asyncio.create_task(
            process_track_splitting(
                session_maker, lalal_client, file_storage_service, notifier
            )
        )

        try:
            await asyncio.shield(task)
            await asyncio.sleep(30)  # Проверяем каждые 30 секунд
        except asyncio.CancelledError:
            logger.info(
                "Task cancelled", extra={"task": task_name, "iteration": iteration}
            )
            if not task.done():
                await task
            break
        except Exception as e:
            logger.exception(
                "Task failed",
                extra={"task": task_name, "iteration": iteration},
                exc_info=e,
            )
            if notifier:
                await notifier.send_error_notification(
                    error=e,
                    context=f"{task_name} (iteration #{iteration})",
                )
            await asyncio.sleep(30)


async def process_karaoke_transcription(
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
):
    """Фоновая задача для обработки транскрипции"""
    iteration = 0
    task_name = "process_karaoke_transcription"

    while True:
        iteration += 1
        logger.info(
            "Processing karaoke transcription",
            extra={"task": task_name, "iteration": iteration},
        )

        task = asyncio.create_task(
            process_transcription(
                session_maker, assemblyai_client, file_storage_service, notifier
            )
        )

        try:
            await asyncio.shield(task)
            await asyncio.sleep(30)  # Проверяем каждые 30 секунд
        except asyncio.CancelledError:
            logger.info(
                "Task cancelled", extra={"task": task_name, "iteration": iteration}
            )
            if not task.done():
                await task
            break
        except Exception as e:
            logger.exception(
                "Task failed",
                extra={"task": task_name, "iteration": iteration},
                exc_info=e,
            )
            if notifier:
                await notifier.send_error_notification(
                    error=e,
                    context=f"{task_name} (iteration #{iteration})",
                )
            await asyncio.sleep(30)
