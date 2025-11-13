import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from application.karaoke_tracks.models.models import (
    TrackCreatingTaskStatus,
    TrackCreatingTaskStep,
    TrackCreatingTaskStepType,
    TrackCreatingTaskStepStatus,
    TrackCreatingTaskLog,
    SubtitleItem,
)
from application.karaoke_tracks.services.assemblyai_client import IAssemblyAIClient
from application.karaoke_tracks.services.assemblyai_models import SubtitleFormat
from core.notifier.notifier import Notifier
from core.errors import BaseError

logger = logging.getLogger(__name__)


async def get_subtitles_result(
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    notifier: Notifier,
) -> None:
    """Получение результатов субтитров из AssemblyAI"""

    # Получаем список шагов для обработки в отдельной транзакции
    async with session_maker() as session:
        steps = list(
            (
                await session.execute(
                    select(TrackCreatingTaskStep)
                    .join(TrackCreatingTaskStep.task)
                    .where(
                        TrackCreatingTaskStep.step
                        == TrackCreatingTaskStepType.SUBTITLES
                    )
                    .where(
                        TrackCreatingTaskStep.status.in_(
                            [
                                TrackCreatingTaskStepStatus.INIT,
                                TrackCreatingTaskStepStatus.IN_PROCESS,
                                TrackCreatingTaskStepStatus.FAILED,
                            ]
                        )
                    )
                    .where(TrackCreatingTaskStep.retries < 5)
                    .where(TrackCreatingTaskStep.data.has_key("transcript_id"))
                    .options(selectinload(TrackCreatingTaskStep.task))
                    .order_by(TrackCreatingTaskStep.created_at)
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )

    logger.info(f"Found {len(steps)} steps to process for subtitles results")

    for step in steps:
        await _get_single_subtitles_result(
            step, session_maker, assemblyai_client, notifier
        )


async def _get_single_subtitles_result(
    step: TrackCreatingTaskStep,
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    notifier: Notifier,
) -> None:
    """Получение результатов субтитров для одного шага"""
    try:
        transcript_id = step.data.get("transcript_id")

        # Используем AssemblyAIClient для получения субтитров
        async with assemblyai_client:
            get_result = await assemblyai_client.get_subtitles(
                transcript_id=transcript_id,
                subtitle_format=SubtitleFormat.VTT,
                chars_per_caption=80,  # оптимальная длина для караоке
            )

            # Преобразуем субтитры в наш формат
            subtitle_items = []
            for subtitle in get_result.response.subtitles:
                subtitle_items.append(
                    SubtitleItem(
                        text=subtitle.text,
                        start=subtitle.time_start,
                        end=subtitle.time_end,
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
                                    TrackCreatingTaskStepStatus.INIT,
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

                # Сохраняем субтитры в задачу
                locked_step.task.subtitles = subtitle_items
                locked_step.task.status = TrackCreatingTaskStatus.SUBTITLES_COMPLETED

                # Завершаем шаг
                locked_step.status = TrackCreatingTaskStepStatus.COMPLETED
                locked_step.processed_at = datetime.now(timezone.utc)
                locked_step.data = {
                    **locked_step.data,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "subtitles_count": len(subtitle_items),
                    "get_api_context": get_result.context.model_dump(),
                }

                # Логируем успех
                log = TrackCreatingTaskLog(
                    task_id=locked_step.task_id,
                    step_id=locked_step.id,
                    data={
                        "message": "Successfully processed subtitles result",
                        "transcript_id": transcript_id,
                        "subtitles_count": len(subtitle_items),
                        "get_api_context": get_result.context.model_dump(),
                    },
                )
                session.add(log)

                await session.commit()

                logger.info(
                    f"Successfully processed subtitles result for task {locked_step.task_id}",
                    extra={
                        "task_id": locked_step.task_id,
                        "subtitles_count": len(subtitle_items),
                        "get_api_context": get_result.context.model_dump(),
                    },
                )

    except Exception as e:
        await _handle_subtitles_error(step, e, session_maker, notifier)


async def _handle_subtitles_error(
    step: TrackCreatingTaskStep,
    error: Exception,
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Обработка ошибки при получении субтитров"""
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

            # Формируем данные ошибки
            error_data = {
                "error": str(error),
                "error_type": type(error).__name__,
                "retry_count": locked_step.retries,
                "transcript_id": locked_step.data.get("transcript_id"),
            }

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
                f"Failed to get subtitles result for task {locked_step.task_id} ({error_type})",
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
                    context=f"Final subtitles result failure for task {locked_step.task_id}",
                )

    except Exception as inner_error:
        logger.error(
            f"Failed to handle subtitles error for step {step.id}: {inner_error}",
            extra={"step_id": step.id},
            exc_info=True,
        )
