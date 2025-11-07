import logging
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from application.karaoke_tracks.models.models import (
    TrackCreatingTask,
    TrackCreatingTaskStatus,
    TrackCreatingTaskStep,
    TrackCreatingTaskStepType,
    TrackCreatingTaskStepStatus,
)
from core.notifier.notifier import Notifier

logger = logging.getLogger(__name__)


async def init_transcription(
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Инициализация транскрипции - создание шагов для задач"""

    # Получаем список задач для обработки в отдельной транзакции
    async with session_maker() as session:
        tasks = list(
            (
                await session.execute(
                    select(TrackCreatingTask)
                    .where(
                        TrackCreatingTask.status
                        == TrackCreatingTaskStatus.SPLIT_COMPLETED
                    )
                    .where(
                        ~TrackCreatingTask.steps.any(
                            TrackCreatingTaskStep.step
                            == TrackCreatingTaskStepType.TRANSCRIPT
                        )
                    )
                    .options(selectinload(TrackCreatingTask.steps))
                    .order_by(TrackCreatingTask.created_at)
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )

    logger.info(f"Found {len(tasks)} tasks to initialize for transcription")

    # Обрабатываем каждую задачу в отдельной транзакции
    for task in tasks:
        await _init_single_task_transcription(task, session_maker, notifier)


async def _init_single_task_transcription(
    task,
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Инициализация транскрипции для одной задачи"""
    try:
        async with session_maker() as session:
            # Блокируем задачу для обновления
            locked_task = await session.execute(
                select(TrackCreatingTask)
                .where(TrackCreatingTask.id == task.id)
                .where(
                    TrackCreatingTask.status == TrackCreatingTaskStatus.SPLIT_COMPLETED
                )
                .options(selectinload(TrackCreatingTask.steps))
                .with_for_update()
            )
            locked_task = locked_task.scalar_one_or_none()

            if not locked_task:
                return

            # Проверяем, нет ли уже шага TRANSCRIPT
            existing_transcript_step = next(
                (
                    step
                    for step in locked_task.steps
                    if step.step == TrackCreatingTaskStepType.TRANSCRIPT
                ),
                None,
            )
            if existing_transcript_step:
                return

            # Создаем шаг TRANSCRIPT
            transcript_step = TrackCreatingTaskStep(
                task_id=locked_task.id,
                step=TrackCreatingTaskStepType.TRANSCRIPT,
                status=TrackCreatingTaskStepStatus.INIT,
                data={},
                retries=0,
            )

            # Обновляем статус задачи
            locked_task.status = TrackCreatingTaskStatus.IN_TRANSCRIPT_PROCESS

            session.add(transcript_step)
            session.add(locked_task)
            await session.commit()

            logger.info(
                f"Initialized transcription process for task {locked_task.id}",
                extra={"task_id": locked_task.id},
            )

    except Exception as e:
        logger.error(
            f"Failed to initialize transcription for task {task.id}: {e}",
            extra={"task_id": task.id},
            exc_info=True,
        )
        await notifier.send_error_notification(
            error=e,
            context=f"Transcription initialization error for task {task.id}",
        )
