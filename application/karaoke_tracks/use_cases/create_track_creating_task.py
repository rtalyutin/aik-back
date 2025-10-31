import uuid
from typing import Union

from application.karaoke_tracks.exceptions import (
    FileProcessingError,
    ExternalServiceError,
)
from application.karaoke_tracks.models.models import (
    TrackCreatingTask,
    TrackCreatingTaskStatus,
)
from core.database.uow import UoW
from core.file_storage.file_storage_service import FileStorageService


async def create_track_creating_task(
    file_content: Union[bytes, str],  # bytes для файла, str для URL
    lang_code: str,
    file_storage_service: FileStorageService,
    uow: UoW,
) -> TrackCreatingTask:
    """
    Use case для создания задачи создания трека
    """
    # Сохраняем файл в S3
    try:
        if isinstance(file_content, bytes):
            # Загружаем из bytes
            file_key = await file_storage_service.upload_file(
                file_content=file_content,
                file_name=f"base_track_{uuid.uuid4()}.mp3",
                content_type="audio/mpeg",
            )
        else:
            # Загружаем из URL
            file_key = await file_storage_service.upload_file_from_url(file_content)
    except Exception as e:
        # Преобразуем любые исключения в наши бизнес-ошибки
        if isinstance(e, (ConnectionError, TimeoutError)):
            raise ExternalServiceError(
                message="Failed to connect to external service",
                details={"service": "file_storage", "error": str(e)},
            )
        else:
            raise FileProcessingError(
                message="Failed to create track creating task",
                details={"error": str(e)},
            )

    async with uow:
        # Создаем задачу
        task = TrackCreatingTask(
            base_track_file=file_key,
            lang_code=lang_code,
            status=TrackCreatingTaskStatus.CREATED,
            split_retries=0,
            transcript_retries=0,
        )

        uow.session.add(task)
        await uow.session.flush()
        await uow.session.refresh(task)

        return task
