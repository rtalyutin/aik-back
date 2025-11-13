import logging
from datetime import datetime, timezone

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


async def init_subtitles(
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Инициализация получения субтитров - создание шагов SUBTITLES"""

    async with session_maker() as session:
        tasks = list(
            (
                await session.execute(
                    select(TrackCreatingTask)
                    .where(
                        TrackCreatingTask.status
                        == TrackCreatingTaskStatus.TRANSCRIPT_COMPLETED
                    )
                    .where(
                        ~TrackCreatingTask.steps.any(
                            TrackCreatingTaskStep.step
                            == TrackCreatingTaskStepType.SUBTITLES
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

    logger.info(f"Found {len(tasks)} tasks to initialize for subtitles")

    for task in tasks:
        await _init_single_task_subtitles(task, session_maker, notifier)


async def _init_single_task_subtitles(
    task: TrackCreatingTask,
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Инициализация получения субтитров для одной задачи"""
    try:
        async with session_maker() as session:
            # Блокируем задачу для обновления
            locked_task = await session.execute(
                select(TrackCreatingTask)
                .where(TrackCreatingTask.id == task.id)
                .where(
                    TrackCreatingTask.status
                    == TrackCreatingTaskStatus.TRANSCRIPT_COMPLETED
                )
                .options(selectinload(TrackCreatingTask.steps))
                .with_for_update()
            )
            locked_task = locked_task.scalar_one_or_none()

            if not locked_task:
                return

            # Находим завершенный шаг транскрипции для получения transcript_id
            transcript_step = next(
                (
                    step
                    for step in locked_task.steps
                    if step.step == TrackCreatingTaskStepType.TRANSCRIPT
                    and step.status == TrackCreatingTaskStepStatus.COMPLETED
                ),
                None,
            )

            if not transcript_step or not transcript_step.data.get("transcript_id"):
                logger.warning(
                    f"No completed transcript step found for task {locked_task.id}"
                )
                return

            transcript_id = transcript_step.data["transcript_id"]

            # Проверяем, нет ли уже шага SUBTITLES
            existing_subtitles_step = next(
                (
                    step
                    for step in locked_task.steps
                    if step.step == TrackCreatingTaskStepType.SUBTITLES
                ),
                None,
            )
            if existing_subtitles_step:
                return

            # Создаем шаг SUBTITLES
            subtitles_step = TrackCreatingTaskStep(
                task_id=locked_task.id,
                step=TrackCreatingTaskStepType.SUBTITLES,
                status=TrackCreatingTaskStepStatus.INIT,
                data={
                    "transcript_id": transcript_id,
                    "initialized_at": datetime.now(timezone.utc).isoformat(),
                },
                retries=0,
            )

            # Обновляем статус задачи
            locked_task.status = TrackCreatingTaskStatus.IN_SUBTITLES_PROCESS

            session.add(subtitles_step)
            session.add(locked_task)
            await session.commit()

            logger.info(
                f"Initialized subtitles process for task {locked_task.id}",
                extra={
                    "task_id": locked_task.id,
                    "transcript_id": transcript_id,
                },
            )

    except Exception as e:
        logger.error(
            f"Failed to initialize subtitles for task {task.id}: {e}",
            extra={"task_id": task.id},
            exc_info=True,
        )
        await notifier.send_error_notification(
            error=e,
            context=f"Subtitles initialization error for task {task.id}",
        )
