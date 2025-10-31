import uuid
from typing import Optional

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, UploadFile, File, Form, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from application.karaoke_tracks.exceptions import (
    InvalidFileOrUrlError,
    FileProcessingError,
    TrackCreatingTaskNotFoundException,
    KaraokeTrackNotFoundException,
)
from application.karaoke_tracks.http.requests import (
    CreateTrackTaskFromUrlRequest,
)
from application.karaoke_tracks.http.responses import (
    TrackCreatingTaskResponse,
    KaraokeTrackResponse,
)
from application.karaoke_tracks.models.models import (
    TrackCreatingTask,
    KaraokeTrack,
    TrackCreatingTaskStatus,
)
from application.karaoke_tracks.use_cases import create_track_creating_task
from core.database.uow import UoW
from core.file_storage.file_storage_service import FileStorageService
from core.auth import authentication_middleware
from core.handlers.handlers import get_responses_for_exceptions
from core.responses.responses import BaseListDataResponse, BaseDataResponse

router = APIRouter(
    prefix="/karaoke-tracks",
    tags=["karaoke-tracks"],
    dependencies=[Depends(authentication_middleware)],
)


@router.post(
    "/create-task-from-file",
    response_model=BaseDataResponse[TrackCreatingTaskResponse],
    responses=get_responses_for_exceptions(
        InvalidFileOrUrlError,
        FileProcessingError,
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def create_track_task_from_file(
    file: UploadFile = File(..., description="Аудиофайл"),
    lang_code: str = Form(..., description="Код языка (например, 'ru', 'en')"),
    file_storage_service: FromDishka[FileStorageService] = FromDishka(),
    uow: FromDishka[UoW] = FromDishka(),
) -> BaseDataResponse[TrackCreatingTaskResponse]:
    """
    Создание задачи для создания караоке-трека из загружаемого файла
    """
    if not file:
        raise InvalidFileOrUrlError(message="File must be provided")

    try:
        file_content = await file.read()
        if not file_content:
            raise FileProcessingError(message="Uploaded file is empty")

        task = await create_track_creating_task(
            file_content=file_content,
            lang_code=lang_code,
            file_storage_service=file_storage_service,
            uow=uow,
        )

        return BaseDataResponse[TrackCreatingTaskResponse](
            data=TrackCreatingTaskResponse.from_orm(task)
        )

    except Exception as e:
        raise FileProcessingError(
            message=f"Error processing file: {str(e)}",
            details={"filename": file.filename},
        )


@router.post(
    "/create-task-from-url",
    response_model=BaseDataResponse[TrackCreatingTaskResponse],
    responses=get_responses_for_exceptions(
        InvalidFileOrUrlError,
        FileProcessingError,
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def create_track_task_from_url(
    request: CreateTrackTaskFromUrlRequest,
    file_storage_service: FromDishka[FileStorageService] = FromDishka(),
    uow: FromDishka[UoW] = FromDishka(),
) -> BaseDataResponse[TrackCreatingTaskResponse]:
    """
    Создание задачи для создания караоке-трека из URL файла
    """
    try:
        task = await create_track_creating_task(
            file_content=str(request.file_url),
            lang_code=request.lang_code,
            file_storage_service=file_storage_service,
            uow=uow,
        )

        return BaseDataResponse[TrackCreatingTaskResponse](
            data=TrackCreatingTaskResponse.from_orm(task)
        )

    except Exception as e:
        raise FileProcessingError(
            message=f"Error processing URL: {str(e)}",
            details={"file_url": str(request.file_url)},
        )


@router.get(
    "/tasks/{task_id}",
    response_model=BaseDataResponse[TrackCreatingTaskResponse],
    responses=get_responses_for_exceptions(
        TrackCreatingTaskNotFoundException,
        with_validation_error=False,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def get_track_creating_task(
    task_id: uuid.UUID,
    uow: FromDishka[UoW] = FromDishka(),
) -> BaseDataResponse[TrackCreatingTaskResponse]:
    """
    Получение информации о задаче создания трека
    """
    async with uow:
        task = await uow.session.execute(
            select(TrackCreatingTask)
            .where(TrackCreatingTask.id == task_id)
            .options(
                selectinload(TrackCreatingTask.result_track),
                selectinload(TrackCreatingTask.logs),
            )
        )
        task = task.scalar_one_or_none()

        if not task:
            raise TrackCreatingTaskNotFoundException(task_id)

        return BaseDataResponse[TrackCreatingTaskResponse](
            data=TrackCreatingTaskResponse.from_orm(task)
        )


@router.get(
    "/tasks",
    response_model=BaseListDataResponse[TrackCreatingTaskResponse],
    responses=get_responses_for_exceptions(
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def list_track_creating_tasks(
    status: Optional[TrackCreatingTaskStatus] = Query(
        None, description="Статус задачи для фильтрации"
    ),
    limit: int = Query(20, description="Лимит записей в результате", le=100, ge=1),
    offset: int = Query(0, description="Смещение для пагинации", ge=0),
    uow: FromDishka[UoW] = FromDishka(),
) -> BaseListDataResponse[TrackCreatingTaskResponse]:
    """
    Получение списка задач создания треков
    """
    async with uow:
        query = select(TrackCreatingTask).order_by(TrackCreatingTask.created_at.desc())

        if status:
            query = query.where(TrackCreatingTask.status == status.value)

        query = query.offset(offset).limit(limit)

        tasks = await uow.session.execute(query)
        tasks = tasks.scalars().all()

        return BaseListDataResponse[TrackCreatingTaskResponse](
            data=[TrackCreatingTaskResponse.from_orm(task) for task in tasks]
        )


@router.get(
    "/{track_id}",
    response_model=BaseDataResponse[KaraokeTrackResponse],
    responses=get_responses_for_exceptions(
        KaraokeTrackNotFoundException,
        with_validation_error=False,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def get_karaoke_track(
    track_id: uuid.UUID,
    uow: FromDishka[UoW] = FromDishka(),
) -> BaseDataResponse[KaraokeTrackResponse]:
    """
    Получение информации о готовом караоке-треке
    """
    async with uow:
        track = await uow.session.execute(
            select(KaraokeTrack)
            .where(KaraokeTrack.id == track_id)
            .options(selectinload(KaraokeTrack.creating_task))
        )
        track = track.scalar_one_or_none()

        if not track:
            raise KaraokeTrackNotFoundException(track_id)

        return BaseDataResponse[KaraokeTrackResponse](
            data=KaraokeTrackResponse.from_orm(track)
        )


@router.get(
    "",
    response_model=BaseListDataResponse[KaraokeTrackResponse],
    responses=get_responses_for_exceptions(
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def list_karaoke_tracks(
    limit: int = Query(20, description="Лимит записей в результате", le=100, ge=1),
    offset: int = Query(0, description="Смещение для пагинации", ge=0),
    uow: FromDishka[UoW] = FromDishka(),
) -> BaseListDataResponse[KaraokeTrackResponse]:
    """
    Получение списка готовых караоке-треков
    """
    async with uow:
        query = select(KaraokeTrack).order_by(KaraokeTrack.created_at.desc())
        query = query.offset(offset).limit(limit)

        tracks = await uow.session.execute(query)
        tracks = tracks.scalars().all()

        return BaseListDataResponse[KaraokeTrackResponse](
            data=[KaraokeTrackResponse.from_orm(track) for track in tracks]
        )
