import asyncio
import logging
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from application.karaoke_tracks.use_cases.init_track_splitting import (
    init_track_splitting,
)
from application.karaoke_tracks.use_cases.send_track_to_split import (
    send_track_to_split,
)
from application.karaoke_tracks.use_cases.get_result_track_splitting import (
    get_result_track_splitting,
)
from application.karaoke_tracks.use_cases.init_transcription import (
    init_transcription,
)
from application.karaoke_tracks.use_cases.send_track_to_transcription import (
    send_track_to_transcription,
)
from application.karaoke_tracks.use_cases.get_transcription_result import (
    get_transcription_result,
)
from application.karaoke_tracks.services.lalal_client import ILalalClient
from application.karaoke_tracks.services.assemblyai_client import IAssemblyAIClient
from core.file_storage.file_storage_service import FileStorageService
from core.notifier.notifier import Notifier

logger = logging.getLogger(__name__)


async def process_karaoke_track_splitting_init(
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
):
    """Фоновая задача для инициализации разделения треков"""
    iteration = 0
    task_name = "process_karaoke_track_splitting_init"

    while True:
        iteration += 1
        logger.info(
            "Processing karaoke track splitting initialization",
            extra={"task": task_name, "iteration": iteration},
        )

        task = asyncio.create_task(init_track_splitting(session_maker, notifier))

        try:
            await asyncio.shield(task)
            await asyncio.sleep(10)  # Проверяем каждые 10 секунд
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
            await asyncio.sleep(10)


async def process_karaoke_track_splitting_send(
    session_maker: async_sessionmaker[AsyncSession],
    lalal_client: ILalalClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
):
    """Фоновая задача для отправки треков на разделение"""
    iteration = 0
    task_name = "process_karaoke_track_splitting_send"

    while True:
        iteration += 1
        logger.info(
            "Processing karaoke track splitting send",
            extra={"task": task_name, "iteration": iteration},
        )

        task = asyncio.create_task(
            send_track_to_split(
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


async def process_karaoke_track_splitting_results(
    session_maker: async_sessionmaker[AsyncSession],
    lalal_client: ILalalClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
):
    """Фоновая задача для получения результатов разделения"""
    iteration = 0
    task_name = "process_karaoke_track_splitting_results"

    while True:
        iteration += 1
        logger.info(
            "Processing karaoke track splitting results",
            extra={"task": task_name, "iteration": iteration},
        )

        task = asyncio.create_task(
            get_result_track_splitting(
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


async def process_karaoke_transcription_init(
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
):
    """Фоновая задача для инициализации транскрипции"""
    iteration = 0
    task_name = "process_karaoke_transcription_init"

    while True:
        iteration += 1
        logger.info(
            "Processing karaoke transcription initialization",
            extra={"task": task_name, "iteration": iteration},
        )

        task = asyncio.create_task(init_transcription(session_maker, notifier))

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


async def process_karaoke_transcription_send(
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
):
    """Фоновая задача для отправки транскрипции в AssemblyAI"""
    iteration = 0
    task_name = "process_karaoke_transcription_send"

    while True:
        iteration += 1
        logger.info(
            "Processing karaoke transcription send",
            extra={"task": task_name, "iteration": iteration},
        )

        task = asyncio.create_task(
            send_track_to_transcription(
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


async def process_karaoke_transcription_results(
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
):
    """Фоновая задача для получения результатов транскрипции"""
    iteration = 0
    task_name = "process_karaoke_transcription_results"

    while True:
        iteration += 1
        logger.info(
            "Processing karaoke transcription results",
            extra={"task": task_name, "iteration": iteration},
        )

        task = asyncio.create_task(
            get_transcription_result(session_maker, assemblyai_client, notifier)
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
