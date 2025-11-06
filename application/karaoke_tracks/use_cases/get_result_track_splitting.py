import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, DateTime

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
import config

logger = logging.getLogger(__name__)


class SplitResultsNotFoundError(BaseError):
    status_code = 424
    code: str = "split_results_not_found"
    message: str = "Split results not found in LALAL AI response"

    def __init__(self, lalal_task_id: str, api_context: dict, details: dict = None):
        self.lalal_task_id = lalal_task_id
        self.api_context = api_context
        self.details = details or {}
        super().__init__(
            message=f"Split results for task {lalal_task_id} not found in response",
            details={
                "lalal_task_id": lalal_task_id,
                "api_context": api_context,
                **self.details,
            },
        )


class SplitResultsNotReadyError(BaseError):
    status_code = 424
    code: str = "split_results_not_ready"
    message: str = "Split results are not ready yet"

    def __init__(self, lalal_task_id: str, api_context: dict, details: dict = None):
        self.lalal_task_id = lalal_task_id
        self.api_context = api_context
        self.details = details or {}
        super().__init__(
            message=f"Split results for task {lalal_task_id} are not ready",
            details={
                "lalal_task_id": lalal_task_id,
                "api_context": api_context,
                **self.details,
            },
        )


async def get_result_track_splitting(
    session_maker: async_sessionmaker[AsyncSession],
    lalal_client: ILalalClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
) -> None:
    """Получение результатов разделения из LALAL AI"""
    time_threshold = datetime.now(timezone.utc) - timedelta(
        seconds=config.get_config().LALAL_AI_GET_SPLIT_RESULT_THRESHOLD
    )

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
                                TrackCreatingTaskStepStatus.IN_PROCESS,
                                TrackCreatingTaskStepStatus.FAILED,
                            ]
                        )
                    )
                    .where(TrackCreatingTaskStep.retries < 5)
                    .where(TrackCreatingTaskStep.data.has_key("lalal_file_id"))
                    # Фильтруем по времени - только те, где split_requested_at старше 30 секунд
                    .where(
                        func.cast(
                            TrackCreatingTaskStep.data["split_requested_at"].astext,
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

    logger.info(
        f"Found {len(steps)} steps to check for split results",
        extra={"time_threshold": time_threshold.isoformat()},
    )

    # Обрабатываем каждый шаг в отдельной транзакции
    for step in steps:
        await _get_single_result_track_splitting(
            step, session_maker, lalal_client, file_storage_service, notifier
        )


async def _get_single_result_track_splitting(
    step: TrackCreatingTaskStep,
    session_maker: async_sessionmaker[AsyncSession],
    lalal_client: ILalalClient,
    file_storage_service: FileStorageService,
    notifier: Notifier,
) -> None:
    """Получение результатов разделения для одного шага"""
    try:
        lalal_file_id = step.data.get("lalal_file_id")
        lalal_task_id = step.data.get("lalal_task_id")

        # Используем LalalClient как менеджер контекста для операций с API
        async with lalal_client:
            # Проверяем статус в LALAL AI
            status_result_with_context = await lalal_client.check_split_status(
                lalal_file_id
            )
            status_result = status_result_with_context.response
            file_result = status_result.result.get(lalal_file_id)

            if not file_result:
                # Вместо общего Exception используем наше специфичное исключение
                raise SplitResultsNotFoundError(
                    lalal_task_id=lalal_task_id,
                    api_context=status_result_with_context.context.model_dump(),
                    details={
                        "lalal_file_id": lalal_file_id,
                        "response_status": status_result.status,
                        "available_results": list(status_result.result.keys()),
                    },
                )

            if file_result.task.state == "progress":
                return

            # Обрабатываем результаты
            if file_result and file_result.split:
                # Сохраняем vocal и instrumental файлы
                vocal_key = await file_storage_service.upload_file_from_url(
                    file_result.split.stem_track, f"vocal_{step.task_id}.mp3"
                )
                instrumental_key = await file_storage_service.upload_file_from_url(
                    file_result.split.back_track, f"instrumental_{step.task_id}.mp3"
                )

                # Обновляем задачу в транзакции с блокировкой
                async with session_maker() as session:
                    # Блокируем шаг и задачу для обновления
                    locked_step = await session.execute(
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
                    locked_step = locked_step.scalar_one_or_none()

                    if not locked_step:
                        return

                    # Обновляем задачу
                    locked_step.task.vocal_file = vocal_key
                    locked_step.task.instrumental_file = instrumental_key
                    locked_step.task.status = TrackCreatingTaskStatus.SPLIT_COMPLETED

                    # Завершаем шаг
                    locked_step.status = TrackCreatingTaskStepStatus.COMPLETED
                    locked_step.processed_at = datetime.now(timezone.utc)

                    # Логируем успех
                    log = TrackCreatingTaskLog(
                        task_id=locked_step.task_id,
                        step_id=locked_step.id,
                        data={
                            "message": "Successfully processed split results",
                            "vocal_file": vocal_key,
                            "instrumental_file": instrumental_key,
                            "file_duration": file_result.split.duration,
                            "api_context": status_result_with_context.context.model_dump(),
                        },
                    )
                    session.add(log)

                    await session.commit()

                    logger.info(
                        f"Successfully processed split results for task {locked_step.task_id}",
                        extra={
                            "task_id": locked_step.task_id,
                            "api_context": status_result_with_context.context.model_dump(),
                        },
                    )
            else:
                # Вместо общего Exception используем наше специфичное исключение
                raise SplitResultsNotFoundError(
                    lalal_task_id=lalal_task_id,
                    api_context=status_result_with_context.context.model_dump(),
                    details={
                        "lalal_file_id": lalal_file_id,
                        "file_result_available": bool(file_result),
                        "split_available": bool(
                            file_result.split if file_result else False
                        ),
                        "task_state": file_result.task.state if file_result else None,
                    },
                )
    except Exception as e:
        await _handle_result_error(step, e, session_maker, notifier)


async def _handle_result_error(
    step: TrackCreatingTaskStep,
    error: Exception,
    session_maker: async_sessionmaker[AsyncSession],
    notifier: Notifier,
) -> None:
    """Обработка ошибки при получении результатов"""
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
                "lalal_task_id": locked_step.data.get("lalal_task_id"),
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
                f"Failed to get split results for task {locked_step.task_id} ({error_type})",
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
                    context=f"Final split result failure for task {locked_step.task_id}",
                )

    except Exception as inner_error:
        logger.error(
            f"Failed to handle result error for step {step.id}: {inner_error}",
            extra={"step_id": step.id},
            exc_info=True,
        )
