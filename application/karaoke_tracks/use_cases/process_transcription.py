import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select

from application.karaoke_tracks.models.models import (
    TrackCreatingTask,
    TrackCreatingTaskStatus,
    TrackCreatingTaskLog,
    TrackCreatingTaskLogStep,
    KaraokeTrack,
    TranscriptItem,
)
from application.karaoke_tracks.services.assemblyai_client import IAssemblyAIClient
from core.file_storage.file_storage_service import FileStorageService
from core.notifier.notifier import Notifier

logger = logging.getLogger(__name__)


async def process_transcription(
    session_maker: async_sessionmaker[AsyncSession],
    assemblyai_client: IAssemblyAIClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
) -> None:
    """Use case для обработки транскрипции вокала"""
    async with session_maker() as session:
        # Находим задачи для обработки (те, что успешно прошли разделение)
        tasks_to_process = [
            TrackCreatingTaskStatus.SPLIT_COMPLETED.value,
            TrackCreatingTaskStatus.TRANSCRIPT_ITERATION_FAILED.value,
        ]

        tasks = list(
            (
                await session.execute(
                    select(TrackCreatingTask)
                    .where(TrackCreatingTask.status.in_(tasks_to_process))
                    .where(
                        TrackCreatingTask.vocal_file.is_not(None)
                    )  # Должен быть вокал
                    .order_by(TrackCreatingTask.split_at)
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )

        for task in tasks:
            await _process_single_task_transcription(
                task, session, assemblyai_client, file_storage_service, notifier
            )


async def _process_single_task_transcription(
    task: TrackCreatingTask,
    session: AsyncSession,
    assemblyai_client: IAssemblyAIClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
):
    """Обработка одной задачи транскрипции"""
    try:
        # Обновляем статус
        task.status = TrackCreatingTaskStatus.TRANSCRIPT_STARTED.value
        session.add(task)

        # Логируем начало
        log = TrackCreatingTaskLog(
            task_id=task.id,
            step=TrackCreatingTaskLogStep.TRANSCRIPT_START.value,
            data={"message": "Starting transcription"},
        )
        session.add(log)
        await session.commit()

        # Получаем URL вокала из S3
        vocal_url = await file_storage_service.get_file_url(task.vocal_file)

        # Вызываем AssemblyAI
        result = await assemblyai_client.transcribe_audio(
            vocal_url, task.lang_code, task.id
        )

        if result.success and result.transcript:
            # Преобразуем результат в нашу модель транскрипции
            transcript_items = _convert_assemblyai_to_transcript(result.transcript)

            # Создаем финальный трек
            karaoke_track = KaraokeTrack(
                base_track_file=task.base_track_file,
                vocal_file=task.vocal_file,
                instrumental_file=task.instrumental_file,
                lang_code=task.lang_code,
                transcript=transcript_items,
            )
            session.add(karaoke_track)
            await session.flush()

            # Обновляем задачу
            task.result_track_id = karaoke_track.id
            task.transcript = transcript_items
            task.status = TrackCreatingTaskStatus.COMPLETED.value
            task.transcribed_at = datetime.now(timezone.utc)

            # Логируем успех
            log = TrackCreatingTaskLog(
                task_id=task.id,
                step=TrackCreatingTaskLogStep.TRANSCRIPT_SUCCESS.value,
                data={
                    "message": "Transcription completed successfully",
                    "transcript_items_count": len(transcript_items),
                },
            )
            session.add(log)

            logger.info(
                f"Successfully processed transcription for task {task.id}",
                extra={"task_id": task.id, "transcript_items": len(transcript_items)},
            )

        else:
            # Обработка ошибки
            task.transcript_retries = (task.transcript_retries or 0) + 1

            if task.transcript_retries >= 5:
                task.status = TrackCreatingTaskStatus.TRANSCRIPT_FINAL_FAILED.value
                error_message = (
                    f"Transcription failed after 5 retries: {result.error_message}"
                )

                # Уведомляем о финальной ошибке
                await notifier.send_error_notification(
                    error=Exception(error_message),
                    context=f"Transcription final failure for task {task.id}",
                )
            else:
                task.status = TrackCreatingTaskStatus.TRANSCRIPT_ITERATION_FAILED.value
                error_message = f"Transcription failed (retry {task.transcript_retries}/5): {result.error_message}"

            # Логируем ошибку
            log = TrackCreatingTaskLog(
                task_id=task.id,
                step=TrackCreatingTaskLogStep.TRANSCRIPT_ERROR.value,
                data={
                    "error": result.error_message,
                    "retry_count": task.transcript_retries,
                },
            )
            session.add(log)

            logger.warning(
                error_message,
                extra={"task_id": task.id, "retry_count": task.transcript_retries},
            )

        await session.commit()

    except Exception as e:
        logger.error(
            f"Error processing transcription for task {task.id}: {e}",
            extra={"task_id": task.id},
            exc_info=True,
        )
        await session.rollback()

        # Уведомляем об ошибке процесса
        await notifier.send_error_notification(
            error=e, context=f"Transcription process error for task {task.id}"
        )


def _convert_assemblyai_to_transcript(assemblyai_data: dict) -> list[TranscriptItem]:
    """Конвертирует данные из AssemblyAI в нашу модель транскрипции"""
    transcript_items = []

    # AssemblyAI возвращает слова в поле 'words'
    words = assemblyai_data.get("words", [])

    for word in words:
        transcript_items.append(
            TranscriptItem(
                text=word.get("text", ""),
                start=int(
                    word.get("start", 0) * 1000
                ),  # Конвертируем секунды в миллисекунды
                end=int(
                    word.get("end", 0) * 1000
                ),  # Конвертируем секунды в миллисекунды
                confidence=word.get("confidence", 0),
                speaker=word.get("speaker"),
            )
        )

    return transcript_items
