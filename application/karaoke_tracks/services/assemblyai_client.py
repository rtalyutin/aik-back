import logging
from abc import abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID
import abc

import httpx
from pydantic import ValidationError, HttpUrl

from application.karaoke_tracks.services.assemblyai_models import (
    TranscriptParams,
    TranscriptResponse,
    SubmitTranscriptResponseWithContext,
    GetTranscriptResponseWithContext,
    ApiResponseContext,
    TranscriptStatus,
    TranscriptLanguageCode,
    SpeechUnderstanding,
    SpeechUnderstandingRequest,
    TranslationRequest,
    SubtitleFormat,
    GetSubtitlesResponseWithContext,
    SubtitleItem,
    SubtitlesResponse,
)
from application.karaoke_tracks.services.assemblyai_exceptions import (
    AssemblyAISubmitError,
    AssemblyAIGetError,
    AssemblyAITranscriptionError,
    AssemblyAISubtitlesError,
    AssemblyAISubtitlesParseError,
)

logger = logging.getLogger(__name__)


class IAssemblyAIClient(abc.ABC):
    """Интерфейс клиента AssemblyAI"""

    @abstractmethod
    async def submit_transcription(
        self, audio_url: str, language_code: str, task_id: UUID
    ) -> SubmitTranscriptResponseWithContext:
        """Создает транскрипцию и возвращает ID с контекстом"""
        pass

    @abstractmethod
    async def get_transcription(
        self, transcript_id: str
    ) -> GetTranscriptResponseWithContext:
        """Получает транскрипцию по ID с контекстом"""
        pass

    @abstractmethod
    async def get_subtitles(
        self,
        transcript_id: str,
        subtitle_format: SubtitleFormat = SubtitleFormat.VTT,
        chars_per_caption: Optional[int] = None,
    ) -> GetSubtitlesResponseWithContext:
        """Получает субтитры для транскрипции с контекстом"""
        pass


class AssemblyAIClient(IAssemblyAIClient):
    """Реализация клиента AssemblyAI"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.assemblyai.com",
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._client = None

    async def __aenter__(self):
        """Контекстный менеджер для клиента"""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "Authorization": self.api_key,
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие клиента при выходе из контекста"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self):
        """Проверяет, что клиент инициализирован"""
        if self._client is None:
            raise RuntimeError(
                "AssemblyAIClient must be used within async context manager"
            )

    def _create_response_context(
        self, response: httpx.Response, parsed_body: Dict[str, Any]
    ) -> ApiResponseContext:
        """Создает контекст ответа"""
        return ApiResponseContext(
            headers=dict(response.headers),
            body=parsed_body,
            status_code=response.status_code,
        )

    async def submit_transcription(
        self, audio_url: str, language_code: str, task_id: UUID
    ) -> SubmitTranscriptResponseWithContext:
        """Создает транскрипцию и возвращает ID с контекстом"""
        self._ensure_client()

        response = None
        parsed_response = None
        error = None

        logger.info(
            "Transcription submission started",
            extra={
                "context": {
                    "audio_url": audio_url,
                    "language_code": language_code,
                    "task_id": str(task_id),
                    "base_url": self.base_url,
                }
            },
        )

        try:
            # Подготавливаем параметры согласно документации
            params = TranscriptParams(
                audio_url=HttpUrl(audio_url),
                auto_chapters=False,
                auto_highlights=False,
                content_safety=False,
                language_code=TranscriptLanguageCode(language_code),
                speech_model=None,
                speaker_labels=True,
                speakers_expected=None,
                language_detection=False,
                punctuate=True,
                multichannel=False,
                format_text=True,
                disfluencies=False,
                entity_detection=True,
                sentiment_analysis=False,
                speech_threshold=0.5,
                speech_understanding=SpeechUnderstanding(
                    request=SpeechUnderstandingRequest(
                        translation=TranslationRequest(
                            target_languages=[language_code, "en"]
                        )
                    )
                )
                if language_code != "en"
                else None,
            )
            request_data = params.model_dump(exclude_none=True, mode="json")

            response = await self._client.post(
                f"{self.base_url}/v2/transcript",
                json=request_data,
            )

            if response.status_code != 200:
                raise AssemblyAISubmitError(
                    message=f"HTTP {response.status_code}: {response.text}",
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                    },
                )

            parsed_response = response.json()
            transcript_response = TranscriptResponse(**parsed_response)

            if transcript_response.status == TranscriptStatus.ERROR:
                raise AssemblyAISubmitError(
                    message=transcript_response.error
                    or "Transcription submission failed",
                    details={"api_response": parsed_response},
                )

            context = self._create_response_context(response, parsed_response)
            return SubmitTranscriptResponseWithContext(
                response=transcript_response, context=context
            )

        except httpx.RequestError as e:
            error = AssemblyAISubmitError(
                message=f"Network error during transcription submission: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        except ValidationError as e:
            error = AssemblyAISubmitError(
                message=f"Validation error during transcription submission: {str(e)}",
                details={"validation_errors": e.errors()},
            )
            raise error from e
        except Exception as e:
            if isinstance(e, AssemblyAISubmitError):
                error = e
                raise error

            error = AssemblyAISubmitError(
                message=f"Unexpected error during transcription submission: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        finally:
            if not error:
                logger.info(
                    "Transcription submission finished success",
                    extra={
                        "context": {
                            "transcript_id": parsed_response.get("id")
                            if parsed_response
                            else None,
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
                    "Transcription submission finished with error",
                    extra={"context": context},
                )

    async def get_transcription(
        self, transcript_id: str
    ) -> GetTranscriptResponseWithContext:
        """Получает транскрипцию по ID с контекстом"""
        self._ensure_client()

        response = None
        parsed_response = None
        error = None

        logger.info(
            "Transcription status check started",
            extra={
                "context": {
                    "transcript_id": transcript_id,
                    "base_url": self.base_url,
                }
            },
        )

        try:
            response = await self._client.get(
                f"{self.base_url}/v2/transcript/{transcript_id}",
            )

            if response.status_code != 200:
                raise AssemblyAIGetError(
                    message=f"HTTP {response.status_code}: {response.text}",
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                    },
                )

            parsed_response = response.json()
            transcript_response = TranscriptResponse(**parsed_response)

            if transcript_response.status == TranscriptStatus.ERROR:
                raise AssemblyAITranscriptionError(
                    message=transcript_response.error or "Transcription failed",
                    details={"api_response": parsed_response},
                )

            context = self._create_response_context(response, parsed_response)
            return GetTranscriptResponseWithContext(
                response=transcript_response, context=context
            )

        except httpx.RequestError as e:
            error = AssemblyAIGetError(
                message=f"Network error during transcription check: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        except ValidationError as e:
            error = AssemblyAIGetError(
                message=f"Validation error during transcription check: {str(e)}",
                details={"validation_errors": e.errors()},
            )
            raise error from e
        except Exception as e:
            if isinstance(e, (AssemblyAIGetError, AssemblyAITranscriptionError)):
                error = e
                raise error

            error = AssemblyAIGetError(
                message=f"Unexpected error during transcription check: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        finally:
            if not error:
                logger.info(
                    "Transcription status check finished success",
                    extra={
                        "context": {
                            "transcript_id": transcript_id,
                            "status": parsed_response.get("status")
                            if parsed_response
                            else None,
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
                    "Transcription status check finished with error",
                    extra={"context": context},
                )

    async def get_subtitles(
        self,
        transcript_id: str,
        subtitle_format: SubtitleFormat = SubtitleFormat.VTT,
        chars_per_caption: Optional[int] = None,
    ) -> GetSubtitlesResponseWithContext:
        """Получает субтитры для транскрипции с контекстом"""
        self._ensure_client()

        response = None
        parsed_response = None
        error = None

        logger.info(
            "Subtitles retrieval started",
            extra={
                "context": {
                    "transcript_id": transcript_id,
                    "subtitle_format": subtitle_format.value,
                    "chars_per_caption": chars_per_caption,
                    "base_url": self.base_url,
                }
            },
        )

        subtitles = []
        try:
            # Подготавливаем параметры запроса
            params = {}
            if chars_per_caption is not None:
                params["chars_per_caption"] = str(chars_per_caption)

            response = await self._client.get(
                f"{self.base_url}/v2/transcript/{transcript_id}/{subtitle_format.value}",
                params=params,
            )

            if response.status_code != 200:
                raise AssemblyAISubtitlesError(
                    message=f"HTTP {response.status_code}: {response.text}",
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                    },
                )

            raw_subtitles = response.text

            # Парсим VTT субтитры
            if subtitle_format == SubtitleFormat.VTT:
                subtitles = self._parse_vtt_subtitles(raw_subtitles)
            else:
                # Для других форматов можно добавить соответствующие парсеры
                raise AssemblyAISubtitlesError(
                    message=f"Unsupported subtitle format: {subtitle_format}",
                    details={"supported_formats": [SubtitleFormat.VTT.value]},
                )

            # Создаем ответ
            subtitles_response = SubtitlesResponse(
                subtitles=subtitles, format=subtitle_format, raw_text=raw_subtitles
            )

            context = self._create_response_context(
                response, {"raw_text": raw_subtitles}
            )
            return GetSubtitlesResponseWithContext(
                response=subtitles_response, context=context
            )

        except httpx.RequestError as e:
            error = AssemblyAISubtitlesError(
                message=f"Network error during subtitles retrieval: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        except ValueError as e:
            error = AssemblyAISubtitlesParseError(
                message=f"Failed to parse subtitles: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        except Exception as e:
            if isinstance(e, (AssemblyAISubtitlesError, AssemblyAISubtitlesParseError)):
                error = e
                raise error

            error = AssemblyAISubtitlesError(
                message=f"Unexpected error during subtitles retrieval: {str(e)}",
                details={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise error from e
        finally:
            if not error:
                logger.info(
                    "Subtitles retrieval finished success",
                    extra={
                        "context": {
                            "transcript_id": transcript_id,
                            "subtitle_format": subtitle_format.value,
                            "subtitles_count": len(subtitles)
                            if "subtitles" in locals()
                            else 0,
                            "status_code": response.status_code if response else None,
                        }
                    },
                )
            else:
                context = {}
                if response:
                    context["status_code"] = response.status_code
                    context["text_response"] = response.text
                context["error_message"] = str(error)
                logger.error(
                    "Subtitles retrieval finished with error",
                    extra={"context": context},
                )

    def _parse_vtt_subtitles(self, vtt_text: str) -> List[SubtitleItem]:
        """
        Парсит VTT текст в список SubtitleItem
        """
        subtitles = []

        # Разделяем на блоки (двойной перенос строки)
        blocks = vtt_text.strip().split("\n\n")

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # Пропускаем заголовок WEBVTT
            if block.startswith("WEBVTT"):
                continue

            try:
                subtitle_item = SubtitleItem.from_vtt_block(block)
                if subtitle_item:
                    subtitles.append(subtitle_item)
            except ValueError as e:
                logger.warning(
                    f"Failed to parse VTT block: {e}",
                    extra={"block": block[:100]},  # Логируем только начало блока
                )
                continue

        # Сортируем по времени начала
        subtitles.sort(key=lambda x: x.time_start)

        return subtitles
