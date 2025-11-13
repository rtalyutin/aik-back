import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, DateTime

import config
from application.karaoke_tracks.models.models import (
    TrackCreatingTaskStatus,
    TrackCreatingTaskStep,
    TrackCreatingTaskStepType,
    TrackCreatingTaskStepStatus,
    TrackCreatingTaskLog,
    WordItem,
)
from application.karaoke_tracks.services import TranscriptStatus
from application.karaoke_tracks.services.assemblyai_client import IAssemblyAIClient
from core.notifier.notifier import Notifier
from core.errors import BaseError

logger = logging.getLogger(__name__)


async def get_transcription_result(
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    notifier: Notifier,
) -> None:
    """Получение результатов транскрипции из AssemblyAI"""
    time_threshold = datetime.now(timezone.utc) - timedelta(
        seconds=config.get_config().ASSEMBLY_AI_GET_TRANSCRIPT_RESULT_THRESHOLD
    )

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
                                TrackCreatingTaskStepStatus.IN_PROCESS,
                                TrackCreatingTaskStepStatus.FAILED,
                            ]
                        )
                    )
                    .where(TrackCreatingTaskStep.retries < 5)
                    .where(TrackCreatingTaskStep.data.has_key("transcript_id"))
                    .where(
                        func.cast(
                            TrackCreatingTaskStep.data["submitted_at"].astext,
                            DateTime(timezone=True),
                        )
                        < time_threshold
                    )
                    .options(selectinload(TrackCreatingTaskStep.task))
                    .order_by(TrackCreatingTaskStep.created_at)
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )

    logger.info(f"Found {len(steps)} steps to check for transcription results")

    # Обрабатываем каждый шаг в отдельной транзакции
    for step in steps:
        await _get_single_transcription_result(
            step, session_maker, assemblyai_client, notifier
        )


async def _get_single_transcription_result(
    step: TrackCreatingTaskStep,
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    notifier: Notifier,
) -> None:
    """Получение результата транскрипции для одного шага"""
    try:
        transcript_id = step.data.get("transcript_id")

        # Используем AssemblyAIClient как менеджер контекста
        async with assemblyai_client:
            # Проверяем статус транскрипции
            get_result = await assemblyai_client.get_transcription(transcript_id)

            # Если транскрипция еще не готова, выходим
            if get_result.response.status not in [
                TranscriptStatus.COMPLETED,
                TranscriptStatus.ERROR,
            ]:
                logger.info(
                    f"Transcription {transcript_id} not ready yet, status: {get_result.response.status.value}",
                    extra={
                        "transcript_id": transcript_id,
                        "status": get_result.response.status.value,
                    },
                )
                return

            # Обрабатываем завершенную транскрипцию
            if get_result.response.status == TranscriptStatus.COMPLETED:
                await _process_completed_transcription(step, get_result, session_maker)
            else:  # status == "error"
                await _process_failed_transcription(
                    step, get_result, session_maker, notifier
                )

    except Exception as e:
        await _handle_result_error(step, e, session_maker, notifier)


async def _process_completed_transcription(
    step: TrackCreatingTaskStep,
    get_result,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Обработка успешно завершенной транскрипции"""
    try:
        # Преобразуем результаты в наш формат
        word_items = []
        if get_result.response.words:
            for word in get_result.response.words:
                word_items.append(
                    WordItem(
                        text=word.text,
                        start=word.start,
                        end=word.end,
                        confidence=word.confidence,
                        speaker=word.speaker,
                    )
                )

        # Сохраняем результаты в транзакции
        async with session_maker() as session:
            # Блокируем шаг и задачу для обновления
            locked_step: Optional[TrackCreatingTaskStep] = (
                await session.execute(
                    select(TrackCreatingTaskStep)
                    .where(TrackCreatingTaskStep.id == step.id)
                    .where(
                        TrackCreatingTaskStep.status.in_(
                            [
                                TrackCreatingTaskStepStatus.IN_PROCESS,
                                TrackCreatingTaskStepStatus.FAILED,
                            ]
                        )
                    )
                    .options(selectinload(TrackCreatingTaskStep.task))
                    .with_for_update()
                )
            ).scalar_one_or_none()

            if not locked_step:
                return

            # Обновляем задачу
            locked_step.task.status = TrackCreatingTaskStatus.TRANSCRIPT_COMPLETED
            locked_step.task.words = word_items

            # Завершаем шаг
            locked_step.status = TrackCreatingTaskStepStatus.COMPLETED
            locked_step.processed_at = datetime.now(timezone.utc)
            locked_step.data = {
                **locked_step.data,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "utterances_count": len(word_items),
                "get_api_context": get_result.context.model_dump(),
            }

            # Логируем успех
            log = TrackCreatingTaskLog(
                task_id=locked_step.task_id,
                step_id=locked_step.id,
                data={
                    "message": "Successfully processed transcription result",
                    "transcript_id": locked_step.data.get("transcript_id"),
                    "words_count": len(word_items),
                    "get_api_context": get_result.context.model_dump(),
                },
            )
            session.add(log)

            await session.commit()

            logger.info(
                f"Successfully processed transcription result for task {locked_step.task_id}",
                extra={
                    "task_id": locked_step.task_id,
                    "words_count": len(word_items),
                    "get_api_context": get_result.context.model_dump(),
                },
            )

    except Exception as e:
        logger.error(
            f"Failed to process completed transcription for step {step.id}: {e}",
            extra={"step_id": step.id},
            exc_info=True,
        )
        raise


async def _process_failed_transcription(
    step: TrackCreatingTaskStep,
    get_result,
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Обработка неудачной транскрипции"""
    error_message = get_result.response.error or "Transcription failed"

    async with session_maker() as session:
        # Блокируем шаг для обновления
        locked_step: Optional[TrackCreatingTaskStep] = (
            await session.execute(
                select(TrackCreatingTaskStep)
                .where(TrackCreatingTaskStep.id == step.id)
                .options(selectinload(TrackCreatingTaskStep.task))
                .with_for_update()
            )
        ).scalar_one_or_none()

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

        # Логируем ошибку
        log = TrackCreatingTaskLog(
            task_id=locked_step.task_id,
            step_id=locked_step.id,
            data={
                "error": error_message,
                "error_type": "transcription_failed",
                "retry_count": locked_step.retries,
                "get_api_context": get_result.context.model_dump(),
            },
        )
        session.add(log)

        await session.commit()

        logger.error(
            f"Transcription failed for task {locked_step.task_id} ({error_type})",
            extra={
                "task_id": locked_step.task_id,
                "retry_count": locked_step.retries,
                "error_message": error_message,
                "get_api_context": get_result.context.model_dump(),
            },
        )

        if error_type == "final":
            from core.errors import BaseError

            class TranscriptionFailedError(BaseError):
                status_code = 500
                code = "transcription_failed"
                message = "Transcription failed in AssemblyAI"

            error = TranscriptionFailedError(details={"error_message": error_message})
            await notifier.send_error_notification(
                error=error,
                context=f"Final transcription failure for task {locked_step.task_id}",
            )


async def _handle_result_error(
    step: TrackCreatingTaskStep,
    error: Exception,
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Обработка ошибки при получении результата транскрипции"""
    try:
        async with session_maker() as session:
            # Блокируем шаг для обновления
            locked_step: Optional[TrackCreatingTaskStep] = (
                await session.execute(
                    select(TrackCreatingTaskStep)
                    .where(TrackCreatingTaskStep.id == step.id)
                    .options(selectinload(TrackCreatingTaskStep.task))
                    .with_for_update()
                )
            ).scalar_one_or_none()

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
                "transcript_id": locked_step.data.get("transcript_id"),
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
                f"Failed to get transcription result for task {locked_step.task_id} ({error_type})",
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
                    context=f"Final transcription result failure for task {locked_step.task_id}",
                )

    except Exception as inner_error:
        logger.error(
            f"Failed to handle result error for step {step.id}: {inner_error}",
            extra={"step_id": step.id},
            exc_info=True,
        )
