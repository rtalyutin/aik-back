import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from application.karaoke_tracks.models.models import (
    TrackCreatingTaskStatus,
    TrackCreatingTaskStep,
    TrackCreatingTaskStepType,
    TrackCreatingTaskStepStatus,
    TrackCreatingTaskLog,
)
from application.karaoke_tracks.services.lalal_client import ILalalClient
from core.file_storage.file_storage_service import FileStorageService
from core.notifier.notifier import Notifier
from core.errors import BaseError

logger = logging.getLogger(__name__)


async def send_track_to_split(
    session_maker: async_sessionmaker[AsyncSession],
    lalal_client: ILalalClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
) -> None:
    """Отправка треков на разделение в LALAL AI"""

    # Получаем список шагов для обработки в отдельной транзакции
    async with session_maker() as session:
        steps = list(
            (
                await session.execute(
                    select(TrackCreatingTaskStep)
                    .join(TrackCreatingTaskStep.task)
                    .where(
                        TrackCreatingTaskStep.step == TrackCreatingTaskStepType.SPLIT
                    )
                    .where(
                        TrackCreatingTaskStep.status.in_(
                            [
                                TrackCreatingTaskStepStatus.INIT,
                                TrackCreatingTaskStepStatus.FAILED,
                            ]
                        )
                    )
                    .where(TrackCreatingTaskStep.retries < 5)
                    .where(~TrackCreatingTaskStep.data.has_key("lalal_task_id"))
                    .options(selectinload(TrackCreatingTaskStep.task))
                    .order_by(TrackCreatingTaskStep.created_at)
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )

    logger.info(f"Found {len(steps)} steps to send for splitting")

    # Обрабатываем каждый шаг в отдельной транзакции
    for step in steps:
        await _send_single_track_to_split(
            step, session_maker, lalal_client, file_storage_service, notifier
        )


async def _send_single_track_to_split(
    step: TrackCreatingTaskStep,
    session_maker: async_sessionmaker[AsyncSession],
    lalal_client: ILalalClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
) -> None:
    """Отправка одного трека на разделение"""
    try:
        # Загружаем файл из S3 (вне транзакции)
        file_content = await file_storage_service.download_file(
            step.task.base_track_file
        )

        # Используем LalalClient как менеджер контекста для операций с API
        async with lalal_client:
            upload_result_with_context = await lalal_client.upload_file(
                file_content, step.task.base_track_file
            )
            upload_result = upload_result_with_context.response
            logger.info(
                f"File was uploaded {upload_result.id}",
                extra={
                    "id": upload_result.id,
                    "api_context": upload_result_with_context.context.model_dump(),
                },
            )

            split_result_with_context = await lalal_client.split_track(upload_result.id)
            split_result = split_result_with_context.response
            logger.info(
                f"File was sent to split {split_result.task_id}",
                extra={
                    "task_id": split_result.task_id,
                    "status": split_result.status,
                    "api_context": split_result_with_context.context.model_dump(),
                },
            )

        # Обновляем шаг в транзакции с блокировкой
        async with session_maker() as session:
            # Блокируем шаг и задачу для обновления
            locked_step = await session.execute(
                select(TrackCreatingTaskStep)
                .where(TrackCreatingTaskStep.id == step.id)
                .where(
                    TrackCreatingTaskStep.status.in_(
                        [
                            TrackCreatingTaskStepStatus.INIT,
                            TrackCreatingTaskStepStatus.FAILED,
                        ]
                    )
                )
                .options(selectinload(TrackCreatingTaskStep.task))
                .with_for_update()
            )
            locked_step = locked_step.scalar_one_or_none()

            if not locked_step:
                return

            # Обновляем шаг
            locked_step.data = {
                "lalal_file_id": upload_result.id,
                "lalal_task_id": split_result.task_id,
                "split_requested_at": datetime.now(timezone.utc).isoformat(),
                "upload_api_context": upload_result_with_context.context.model_dump(),
                "split_api_context": split_result_with_context.context.model_dump(),
            }
            locked_step.status = TrackCreatingTaskStepStatus.IN_PROCESS

            # Логируем успех
            log = TrackCreatingTaskLog(
                task_id=locked_step.task_id,
                step_id=locked_step.id,
                data={
                    "message": "Successfully sent track to LALAL AI for splitting",
                    "lalal_file_id": upload_result.id,
                    "lalal_task_id": split_result.task_id,
                    "upload_api_context": upload_result_with_context.context.model_dump(),
                    "split_api_context": split_result_with_context.context.model_dump(),
                },
            )
            session.add(log)

            await session.commit()

            logger.info(
                f"Successfully sent track {locked_step.task_id} to LALAL AI",
                extra={
                    "task_id": locked_step.task_id,
                    "lalal_task_id": split_result.task_id,
                    "upload_api_context": upload_result_with_context.context.model_dump(),
                    "split_api_context": split_result_with_context.context.model_dump(),
                },
            )

    except Exception as e:
        await _handle_send_error(step, e, session_maker, notifier)


async def _handle_send_error(
    step: TrackCreatingTaskStep,
    error: Exception,
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Обработка ошибки при отправке"""
    try:
        async with session_maker() as session:
            # Блокируем шаг для обновления
            locked_step = await session.execute(
                select(TrackCreatingTaskStep)
                .where(TrackCreatingTaskStep.id == step.id)
                .options(selectinload(TrackCreatingTaskStep.task))
                .with_for_update()
            )
            locked_step = locked_step.scalar_one_or_none()

            if not locked_step:
                return

            # Обновляем шаг с ошибкой
            locked_step.retries += 1
            if locked_step.retries >= 5:
                locked_step.status = TrackCreatingTaskStepStatus.FINAL_FAILED
                locked_step.task.status = TrackCreatingTaskStatus.FAILED
                error_type = "final"
            else:
                locked_step.status = TrackCreatingTaskStepStatus.FAILED
                error_type = "retryable"

            # Формируем данные ошибки для логирования
            error_data = {
                "error": str(error),
                "error_type": type(error).__name__,
                "retry_count": locked_step.retries,
            }

            # Если ошибка унаследована от BaseError, добавляем все ее поля
            if isinstance(error, BaseError):
                error_data.update(
                    {
                        "status_code": getattr(error, "status_code", None),
                        "code": getattr(error, "code", None),
                        "message": getattr(error, "message", None),
                        "details": getattr(error, "details", None),
                    }
                )

            # Логируем ошибку
            log = TrackCreatingTaskLog(
                task_id=locked_step.task_id,
                step_id=locked_step.id,
                data=error_data,
            )
            session.add(log)

            await session.commit()

            logger.error(
                f"Failed to send track {locked_step.task_id} to LALAL AI ({error_type})",
                extra={
                    "task_id": locked_step.task_id,
                    "retry_count": locked_step.retries,
                    "error_data": error_data,
                },
                exc_info=True,
            )

            if error_type == "final":
                await notifier.send_error_notification(
                    error=error,
                    context=f"Final split send failure for task {locked_step.task_id}",
                )

    except Exception as inner_error:
        logger.error(
            f"Failed to handle send error for step {step.id}: {inner_error}",
            extra={"step_id": step.id},
            exc_info=True,
        )
