import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from application.karaoke_tracks.models.models import (
    TrackCreatingTaskStep,
    TrackCreatingTaskStatus,
    TrackCreatingTaskStepType,
    TrackCreatingTaskStepStatus,
    TrackCreatingTaskLog,
)
from application.karaoke_tracks.services.assemblyai_client import IAssemblyAIClient
from core.file_storage.file_storage_service import FileStorageService
from core.notifier.notifier import Notifier
from core.errors import BaseError

logger = logging.getLogger(__name__)


async def send_track_to_transcription(
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
) -> None:
    """Отправка запросов на транскрипцию в AssemblyAI"""

    # Получаем список шагов для обработки в отдельной транзакции
    async with session_maker() as session:
        steps = list(
            (
                await session.execute(
                    select(TrackCreatingTaskStep)
                    .join(TrackCreatingTaskStep.task)
                    .where(
                        TrackCreatingTaskStep.step
                        == TrackCreatingTaskStepType.TRANSCRIPT
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
                    .where(~TrackCreatingTaskStep.data.has_key("transcript_id"))
                    .options(selectinload(TrackCreatingTaskStep.task))
                    .order_by(TrackCreatingTaskStep.created_at)
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )

    logger.info(f"Found {len(steps)} steps to send for transcription")

    # Обрабатываем каждый шаг в отдельной транзакции
    for step in steps:
        await _send_single_transcription_request(
            step, session_maker, assemblyai_client, file_storage_service, notifier
        )


async def _send_single_transcription_request(
    step: TrackCreatingTaskStep,
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
) -> None:
    """Отправка одного запроса на транскрипцию"""
    try:
        # Получаем URL для вокала из S3
        vocal_file_url = await file_storage_service.get_file_url(
            step.task.vocal_file, expires_in=3600
        )

        # Используем AssemblyAIClient как менеджер контекста
        async with assemblyai_client:
            # Отправляем на транскрипцию
            submit_result = await assemblyai_client.submit_transcription(
                audio_url=vocal_file_url,
                language_code=step.task.lang_code,
                task_id=step.task.id,
            )

            transcript_id = submit_result.response.id
            logger.info(
                f"Transcription submitted for task {step.task.id}",
                extra={
                    "transcript_id": transcript_id,
                    "api_context": submit_result.context.model_dump(),
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
                "transcript_id": transcript_id,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "submit_api_context": submit_result.context.model_dump(),
            }
            locked_step.status = TrackCreatingTaskStepStatus.IN_PROCESS

            # Логируем успех
            log = TrackCreatingTaskLog(
                task_id=locked_step.task_id,
                step_id=locked_step.id,
                data={
                    "message": "Successfully submitted transcription to AssemblyAI",
                    "transcript_id": transcript_id,
                    "submit_api_context": submit_result.context.model_dump(),
                },
            )
            session.add(log)

            await session.commit()

            logger.info(
                f"Successfully submitted transcription for task {locked_step.task_id}",
                extra={
                    "task_id": locked_step.task_id,
                    "transcript_id": transcript_id,
                    "submit_api_context": submit_result.context.model_dump(),
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
    """Обработка ошибки при отправке транскрипции"""
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
                f"Failed to submit transcription for task {locked_step.task_id} ({error_type})",
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
                    context=f"Final transcription submission failure for task {locked_step.task_id}",
                )

    except Exception as inner_error:
        logger.error(
            f"Failed to handle send error for step {step.id}: {inner_error}",
            extra={"step_id": step.id},
            exc_info=True,
        )
