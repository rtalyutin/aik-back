import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select

from application.karaoke_tracks.models.models import (
    TrackCreatingTask,
    TrackCreatingTaskStatus,
    TrackCreatingTaskLog,
    TrackCreatingTaskLogStep,
)
from application.karaoke_tracks.services.lalal_client import ILalalClient
from core.file_storage.file_storage_service import FileStorageService
from core.notifier.notifier import Notifier

logger = logging.getLogger(__name__)


async def process_track_splitting(
    session_maker: async_sessionmaker[AsyncSession],
    lalal_client: ILalalClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
) -> None:
    """Use case для обработки разделения треков на вокал и инструментал"""
    async with session_maker() as session:
        # Находим задачи для обработки
        tasks_to_process = [
            TrackCreatingTaskStatus.CREATED.value,
            TrackCreatingTaskStatus.SPLIT_ITERATION_FAILED.value,
        ]

        tasks = list(
            (
                await session.execute(
                    select(TrackCreatingTask)
                    .where(TrackCreatingTask.status.in_(tasks_to_process))
                    .order_by(TrackCreatingTask.created_at)
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )

        for task in tasks:
            await _process_single_task_splitting(
                task, session, lalal_client, file_storage_service, notifier
            )


async def _process_single_task_splitting(
    task: TrackCreatingTask,
    session: AsyncSession,
    lalal_client: ILalalClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
):
    """Обработка одной задачи разделения трека"""
    try:
        # Обновляем статус
        task.status = TrackCreatingTaskStatus.SPLIT_STARTED.value
        session.add(task)

        # Логируем начало
        log = TrackCreatingTaskLog(
            task_id=task.id,
            step=TrackCreatingTaskLogStep.SPLIT_START.value,
            data={"message": "Starting track separation"},
        )
        session.add(log)
        await session.commit()

        # Получаем URL файла из S3
        audio_url = await file_storage_service.get_file_url(task.base_track_file)

        # Вызываем LALAL.ai
        result = await lalal_client.separate_track(audio_url, task.id)

        if result.success:
            # Сохраняем результаты
            vocal_key = await file_storage_service.upload_file_from_url(
                result.vocal_file_url, f"vocal_{task.id}.mp3"
            )
            instrumental_key = await file_storage_service.upload_file_from_url(
                result.instrumental_file_url, f"instrumental_{task.id}.mp3"
            )

            task.vocal_file = vocal_key
            task.instrumental_file = instrumental_key
            task.status = TrackCreatingTaskStatus.SPLIT_COMPLETED.value
            task.split_at = datetime.now(timezone.utc)

            # Логируем успех
            log = TrackCreatingTaskLog(
                task_id=task.id,
                step=TrackCreatingTaskLogStep.SPLIT_SUCCESS.value,
                data={"message": "Track separation completed successfully"},
            )
            session.add(log)

            logger.info(
                f"Successfully processed track splitting for task {task.id}",
                extra={"task_id": task.id},
            )

        else:
            # Обработка ошибки
            task.split_retries = (task.split_retries or 0) + 1

            if task.split_retries >= 5:
                task.status = TrackCreatingTaskStatus.SPLIT_FINAL_FAILED.value
                error_message = (
                    f"Track splitting failed after 5 retries: {result.error_message}"
                )

                # Уведомляем о финальной ошибке
                await notifier.send_error_notification(
                    error=Exception(error_message),
                    context=f"Track splitting final failure for task {task.id}",
                )
            else:
                task.status = TrackCreatingTaskStatus.SPLIT_ITERATION_FAILED.value
                error_message = f"Track splitting failed (retry {task.split_retries}/5): {result.error_message}"

            # Логируем ошибку
            log = TrackCreatingTaskLog(
                task_id=task.id,
                step=TrackCreatingTaskLogStep.SPLIT_ERROR.value,
                data={"error": result.error_message, "retry_count": task.split_retries},
            )
            session.add(log)

            logger.warning(
                error_message,
                extra={"task_id": task.id, "retry_count": task.split_retries},
            )

        await session.commit()

    except Exception as e:
        logger.error(
            f"Error processing track splitting for task {task.id}: {e}",
            extra={"task_id": task.id},
            exc_info=True,
        )
        await session.rollback()

        # Уведомляем об ошибке процесса
        await notifier.send_error_notification(
            error=e, context=f"Track splitting process error for task {task.id}"
        )
