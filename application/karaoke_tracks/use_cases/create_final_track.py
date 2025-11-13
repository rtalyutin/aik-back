import logging
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from application.karaoke_tracks.models.models import (
    TrackCreatingTaskStatus,
    TrackCreatingTaskLog,
    KaraokeTrack,
    TrackCreatingTask,
)
from application.karaoke_tracks.services import TranscriptService
from core.notifier.notifier import Notifier

logger = logging.getLogger(__name__)


async def create_final_track(
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Создание финального трека после завершения всех шагов"""

    async with session_maker() as session:
        tasks = list(
            (
                await session.execute(
                    select(TrackCreatingTask)
                    .where(
                        TrackCreatingTask.status.in_(
                            [
                                TrackCreatingTaskStatus.SUBTITLES_COMPLETED,
                            ]
                        )
                    )
                    .where(TrackCreatingTask.result_track_id.is_(None))
                    .options(
                        selectinload(TrackCreatingTask.steps),
                        selectinload(TrackCreatingTask.result_track),
                    )
                    .order_by(TrackCreatingTask.created_at)
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )

    logger.info(f"Found {len(tasks)} tasks for final track creation")

    for task in tasks:
        await _create_single_final_track(task, session_maker, notifier)


async def _create_single_final_track(
    task,
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Создание финального трека для одной задачи"""
    try:
        async with session_maker() as session:
            # Блокируем задачу для обновления
            locked_task = await session.execute(
                select(TrackCreatingTask)
                .where(TrackCreatingTask.id == task.id)
                .where(TrackCreatingTask.result_track_id.is_(None))
                .options(
                    selectinload(TrackCreatingTask.steps),
                    selectinload(TrackCreatingTask.result_track),
                )
                .with_for_update()
            )
            locked_task = locked_task.scalar_one_or_none()

            if not locked_task:
                return

            # Создаем транскрипцию из words и subtitles
            transcript = []
            if locked_task.words and locked_task.subtitles:
                transcript = TranscriptService.create_transcript(
                    words=locked_task.words, subtitles=locked_task.subtitles
                )

                # Валидируем покрытие транскрипции
                coverage_stats = TranscriptService.validate_transcript_timing(
                    transcript=transcript
                )

                logger.info(
                    f"Transcript created for task {locked_task.id}",
                    extra={
                        "task_id": locked_task.id,
                        "transcript_items": len(transcript),
                        "coverage_stats": coverage_stats,
                    },
                )

            # Создаем трек
            track = KaraokeTrack(
                base_track_file=locked_task.base_track_file,
                vocal_file=locked_task.vocal_file,
                instrumental_file=locked_task.instrumental_file,
                lang_code=locked_task.lang_code,
                transcript=transcript,
            )
            session.add(track)
            await session.flush()

            # Связываем задачу с треком
            locked_task.result_track_id = track.id
            locked_task.status = TrackCreatingTaskStatus.COMPLETED

            # Логируем создание
            log = TrackCreatingTaskLog(
                task_id=locked_task.id,
                step_id=None,
                data={
                    "message": "Final track created successfully",
                    "track_id": str(track.id),
                },
            )
            session.add(log)

            await session.commit()

            logger.info(
                f"Successfully created final track for task {locked_task.id}",
                extra={"task_id": locked_task.id, "track_id": str(track.id)},
            )

    except Exception as e:
        logger.error(
            f"Failed to create final track for task {task.id}: {e}",
            extra={"task_id": task.id},
            exc_info=True,
        )
        await notifier.send_error_notification(
            error=e,
            context=f"Final track creation error for task {task.id}",
        )
