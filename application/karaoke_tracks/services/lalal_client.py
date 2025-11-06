import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from enum import Enum

import httpx
from pydantic import BaseModel, Field

from core.errors import BaseError
import logging

logger = logging.getLogger(__name__)


# Исключения LALAL AI
class LalalAIError(BaseError):
    """Базовое исключение для ошибок LALAL AI API"""

    status_code = 502
    code = "lalal_ai_error"
    message = "LALAL AI service error"


class LalalAIUploadError(LalalAIError):
    """Ошибка загрузки файла"""

    code = "lalal_ai_upload_error"
    message = "Failed to upload file to LALAL AI"


class LalalAISplitError(LalalAIError):
    """Ошибка разделения трека"""

    code = "lalal_ai_split_error"
    message = "Failed to split track with LALAL AI"


class LalalAICheckError(LalalAIError):
    """Ошибка проверки статуса"""

    code = "lalal_ai_check_error"
    message = "Failed to check split status with LALAL AI"


class LalalAICancelError(LalalAIError):
    """Ошибка отмены задачи"""

    code = "lalal_ai_cancel_error"
    message = "Failed to cancel tasks with LALAL AI"


class LalalAITimeoutError(LalalAIError):
    """Таймаут операции"""

    status_code = 504
    code = "lalal_ai_timeout_error"
    message = "LALAL AI operation timeout"


# Enum типы
class StemType(str, Enum):
    VOCALS = "vocals"
    VOICE = "voice"
    DRUM = "drum"
    BASS = "bass"
    PIANO = "piano"
    ELECTRIC_GUITAR = "electric_guitar"
    ACOUSTIC_GUITAR = "acoustic_guitar"
    SYNTHESIZER = "synthesizer"
    STRINGS = "strings"
    WIND = "wind"


class SplitterType(str, Enum):
    PHOENIX = "phoenix"
    ORION = "orion"
    PERSEUS = "perseus"


class NoiseCancellingLevel(int, Enum):
    MILD = 0
    NORMAL = 1
    AGGRESSIVE = 2


# Pydantic модели для ответов API
class SplitPreset(BaseModel):
    """Пресет разделения"""

    task_type: str = Field(..., description="Тип задачи")
    stem_option: List[str] = Field(..., description="Опции стемов")
    splitter: str = Field(..., description="Используемый сплиттер")
    dereverb_enabled: bool = Field(..., description="Включено ли удаление реверберации")
    enhanced_processing_enabled: bool = Field(
        ..., description="Включена ли улучшенная обработка"
    )


class Presets(BaseModel):
    """Пресеты задачи"""

    split: SplitPreset = Field(..., description="Пресет разделения")


class SplitInfo(BaseModel):
    """Информация о разделении"""

    stem: str = Field(..., description="Тип стема")
    duration: int = Field(..., description="Длительность в секундах")
    stem_track: str = Field(..., description="URL стем-трека")
    stem_track_size: int = Field(..., description="Размер стем-трека в байтах")
    back_track: str = Field(..., description="URL бэк-трека")
    back_track_size: int = Field(..., description="Размер бэк-трека в байтах")


class TaskInfo(BaseModel):
    """Информация о задаче"""

    state: str = Field(..., description="Состояние задачи")
    split_id: Optional[str] = Field(None, description="ID разделения")
    error: Optional[str] = Field(None, description="Ошибка задачи")
    progress: Optional[int] = Field(None, description="Прогресс в процентах")


class FileSplitResult(BaseModel):
    """Результат разделения для файла"""

    status: str = Field(..., description="Статус")
    name: Optional[str] = Field(None, description="Имя файла")
    size: Optional[int] = Field(None, description="Размер файла")
    duration: Optional[int] = Field(None, description="Длительность")
    presets: Optional[Presets] = Field(None, description="Пресеты")
    stem: Optional[str] = Field(None, description="Стем")
    splitter: Optional[str] = Field(None, description="Сплиттер")
    preview: Optional[str] = Field(None, description="Превью")
    split: Optional[SplitInfo] = Field(None, description="Информация о разделении")
    player: Optional[str] = Field(None, description="Плеер")
    task: Optional[TaskInfo] = Field(None, description="Информация о задаче")
    task_type: Optional[str] = Field(None, description="Тип задачи")


class CheckResponse(BaseModel):
    """Ответ на запрос проверки статуса"""

    status: str = Field(..., description="Статус ответа")
    result: Dict[str, Optional[FileSplitResult]] = Field(
        ..., description="Результаты по файлам"
    )


class UploadResponse(BaseModel):
    """Ответ на загрузку файла"""

    status: str = Field(..., description="Статус")
    id: Optional[str] = Field(None, description="ID файла")
    size: Optional[int] = Field(None, description="Размер файла")
    duration: Optional[float] = Field(None, description="Длительность")
    expires: Optional[int] = Field(None, description="Время истечения")
    error: Optional[str] = Field(None, description="Ошибка")


class SplitResponse(BaseModel):
    """Ответ на запрос разделения"""

    status: str = Field(..., description="Статус")
    task_id: Optional[str] = Field(None, description="ID задачи")
    error: Optional[str] = Field(None, description="Ошибка")


class CancelResponse(BaseModel):
    """Ответ на отмену задачи"""

    status: str = Field(..., description="Статус")
    error: Optional[str] = Field(None, description="Ошибка")


class VocalInstrumentalSeparationResult(BaseModel):
    """Результат разделения на вокал и инструментал"""

    success: bool = Field(..., description="Успех операции")
    vocal_file_url: Optional[str] = Field(None, description="URL вокала")
    instrumental_file_url: Optional[str] = Field(None, description="URL инструментала")
    file_id: Optional[str] = Field(None, description="ID файла в LALAL AI")


# Расширенные классы для ответов с контекстом
class ApiResponseContext(BaseModel):
    """Контекст API ответа"""

    headers: Dict[str, str]
    body: Dict[str, Any]
    status_code: int


class UploadResponseWithContext(BaseModel):
    """Ответ на загрузку файла с контекстом"""

    response: UploadResponse
    context: ApiResponseContext


class SplitResponseWithContext(BaseModel):
    """Ответ на разделение с контекстом"""

    response: SplitResponse
    context: ApiResponseContext


class CheckResponseWithContext(BaseModel):
    """Ответ на проверку статуса с контекстом"""

    response: CheckResponse
    context: ApiResponseContext


class CancelResponseWithContext(BaseModel):
    """Ответ на отмену с контекстом"""

    response: CancelResponse
    context: ApiResponseContext


# Интерфейс клиента
class ILalalClient(ABC):
    @abstractmethod
    async def upload_file(
        self, audio_content: bytes, filename: str
    ) -> UploadResponseWithContext:
        """Загружает файл и возвращает file_id с контекстом"""
        pass

    @abstractmethod
    async def split_track(
        self, file_id: str, stem: StemType = StemType.VOCALS
    ) -> SplitResponseWithContext:
        """Запускает разделение и возвращает task_id с контекстом"""
        pass

    @abstractmethod
    async def check_split_status(self, file_id: str) -> CheckResponseWithContext:
        """Проверяет статус задач разделения с контекстом"""
        pass

    @abstractmethod
    async def cancel_tasks(self, file_id: str) -> CancelResponseWithContext:
        """Отменяет задачи с контекстом"""
        pass


# Реализация клиента
class LalalClient(ILalalClient):
    def __init__(
        self, api_key: str, base_url: str = "https://www.lalal.ai", timeout: int = 30
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._client = None

    async def __aenter__(self):
        # Создаем новый клиент при каждом входе в контекст
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Закрываем клиент при выходе из контекста
        if self._client:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self):
        """Проверяет, что клиент инициализирован"""
        if self._client is None:
            raise RuntimeError("LalalClient must be used within async context manager")

    def _create_response_context(
        self, response: httpx.Response, parsed_body: Dict[str, Any]
    ) -> ApiResponseContext:
        """Создает контекст ответа"""
        return ApiResponseContext(
            headers=dict(response.headers),
            body=parsed_body,
            status_code=response.status_code,
        )

    async def upload_file(
        self, audio_content: bytes, filename: str
    ) -> UploadResponseWithContext:
        """Загружает файл на сервер LALAL AI и возвращает file_id с контекстом"""
        self._ensure_client()

        response = None
        parsed_response = None
        error = None
        headers = {
            "Authorization": f"license {self.api_key}",
            "Content-Disposition": f"attachment; filename={filename}",
        }
        logger.info(
            "File uploading started",
            extra={
                "context": {
                    "file_name": filename,
                    "base_url": self.base_url,
                }
            },
        )
        try:
            response = await self._client.post(
                f"{self.base_url}/api/upload/", headers=headers, content=audio_content
            )

            if response.status_code != 200:
                raise LalalAIUploadError(
                    message=f"HTTP {response.status_code}: {response.text}",
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                    },
                )

            parsed_response = response.json()
            upload_response = UploadResponse(**parsed_response)

            if upload_response.status != "success":
                raise LalalAIUploadError(
                    message=upload_response.error or "Upload failed",
                    details={"api_response": parsed_response},
                )

            if not upload_response.id:
                raise LalalAIUploadError(
                    message="No file ID in response",
                    details={"api_response": parsed_response},
                )

            context = self._create_response_context(response, parsed_response)
            return UploadResponseWithContext(response=upload_response, context=context)

        except httpx.RequestError as e:
            error = LalalAIUploadError(
                message=f"Network error during upload: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        except Exception as e:
            if isinstance(e, LalalAIError):
                error = e
                raise error

            error = LalalAIUploadError(
                message=f"Unexpected error during upload: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        finally:
            if not error:
                logger.info(
                    "File uploading finished success",
                    extra={
                        "context": {
                            "parsed_response": parsed_response,
                            "status_code": response.status_code if response else None,
                        }
                    },
                )
            else:
                context = {}
                if response:
                    context["status_code"] = response.status_code
                    if parsed_response:
                        context["parsed_response"] = parsed_response
                    else:
                        context["text_response"] = response.text
                context["error_message"] = str(error)
                logger.error(
                    "File uploading finished with error",
                    extra={"context": context},
                )

    async def split_track(
        self, file_id: str, stem: StemType = StemType.VOCALS
    ) -> SplitResponseWithContext:
        """Запускает разделение трека и возвращает task_id с контекстом"""
        self._ensure_client()

        response = None
        parsed_response = None
        error = None

        logger.info(
            "Track splitting started",
            extra={
                "context": {
                    "file_id": file_id,
                    "stem": stem.value,
                    "base_url": self.base_url,
                }
            },
        )

        try:
            params = [{"id": file_id, "stem": stem.value}]

            response = await self._client.post(
                f"{self.base_url}/api/split/",
                headers={"Authorization": f"license {self.api_key}"},
                data={"params": json.dumps(params)},
            )

            if response.status_code != 200:
                raise LalalAISplitError(
                    message=f"HTTP {response.status_code}: {response.text}",
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                    },
                )

            parsed_response = response.json()
            split_response = SplitResponse(**parsed_response)

            if split_response.status != "success":
                raise LalalAISplitError(
                    message=split_response.error or "Split request failed",
                    details={"api_response": parsed_response},
                )

            if not split_response.task_id:
                raise LalalAISplitError(
                    message="No task ID in response",
                    details={"api_response": parsed_response},
                )

            context = self._create_response_context(response, parsed_response)
            return SplitResponseWithContext(response=split_response, context=context)

        except httpx.RequestError as e:
            error = LalalAISplitError(
                message=f"Network error during split: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        except Exception as e:
            if isinstance(e, LalalAIError):
                error = e
                raise error

            error = LalalAISplitError(
                message=f"Unexpected error during split: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        finally:
            if not error:
                logger.info(
                    "Track splitting finished success",
                    extra={
                        "context": {
                            "parsed_response": parsed_response,
                            "status_code": response.status_code if response else None,
                        }
                    },
                )
            else:
                context = {}
                if response:
                    context["status_code"] = response.status_code
                    if parsed_response:
                        context["parsed_response"] = parsed_response
                    else:
                        context["text_response"] = response.text
                context["error_message"] = str(error)
                logger.error(
                    "Track splitting finished with error",
                    extra={"context": context},
                )

    async def check_split_status(self, file_id: str) -> CheckResponseWithContext:
        """Проверяет статус задач разделения с контекстом"""
        self._ensure_client()

        response = None
        parsed_response = None
        error = None

        logger.info(
            "Split status check started",
            extra={
                "context": {
                    "file_id": file_id,
                    "base_url": self.base_url,
                }
            },
        )

        try:
            response = await self._client.post(
                f"{self.base_url}/api/check/",
                headers={"Authorization": f"license {self.api_key}"},
                data={"id": file_id},
            )

            if response.status_code != 200:
                raise LalalAICheckError(
                    message=f"HTTP {response.status_code}: {response.text}",
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                    },
                )

            parsed_response = response.json()
            check_response = CheckResponse(**parsed_response)

            context = self._create_response_context(response, parsed_response)
            return CheckResponseWithContext(response=check_response, context=context)

        except httpx.RequestError as e:
            error = LalalAICheckError(
                message=f"Network error during check: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        except Exception as e:
            if isinstance(e, LalalAIError):
                error = e
                raise error

            error = LalalAICheckError(
                message=f"Unexpected error during check: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        finally:
            if not error:
                logger.info(
                    "Split status check finished success",
                    extra={
                        "context": {
                            "parsed_response": parsed_response,
                            "status_code": response.status_code if response else None,
                        }
                    },
                )
            else:
                context = {}
                if response:
                    context["status_code"] = response.status_code
                    if parsed_response:
                        context["parsed_response"] = parsed_response
                    else:
                        context["text_response"] = response.text
                context["error_message"] = str(error)
                logger.error(
                    "Split status check finished with error",
                    extra={"context": context},
                )

    async def cancel_tasks(self, file_id: str) -> CancelResponseWithContext:
        """Отменяет задачи с контекстом"""
        self._ensure_client()

        response = None
        parsed_response = None
        error = None

        logger.info(
            "Tasks cancellation started",
            extra={
                "context": {
                    "file_id": file_id,
                    "base_url": self.base_url,
                }
            },
        )

        try:
            response = await self._client.post(
                f"{self.base_url}/api/cancel/",
                headers={"Authorization": f"license {self.api_key}"},
                data={"id": file_id},
            )

            if response.status_code != 200:
                raise LalalAICancelError(
                    message=f"HTTP {response.status_code}: {response.text}",
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                    },
                )

            parsed_response = response.json()
            cancel_response = CancelResponse(**parsed_response)

            if cancel_response.status != "success":
                raise LalalAICancelError(
                    message=cancel_response.error or "Cancel request failed",
                    details={"api_response": parsed_response},
                )

            context = self._create_response_context(response, parsed_response)
            return CancelResponseWithContext(response=cancel_response, context=context)

        except httpx.RequestError as e:
            error = LalalAICancelError(
                message=f"Network error during cancel: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        except Exception as e:
            if isinstance(e, LalalAIError):
                error = e
                raise error

            error = LalalAICancelError(
                message=f"Unexpected error during cancel: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        finally:
            if not error:
                logger.info(
                    "Tasks cancellation finished success",
                    extra={
                        "context": {
                            "parsed_response": parsed_response,
                            "status_code": response.status_code if response else None,
                        }
                    },
                )
            else:
                context = {}
                if response:
                    context["status_code"] = response.status_code
                    if parsed_response:
                        context["parsed_response"] = parsed_response
                    else:
                        context["text_response"] = response.text
                context["error_message"] = str(error)
                logger.error(
                    "Tasks cancellation finished with error",
                    extra={"context": context},
                )
