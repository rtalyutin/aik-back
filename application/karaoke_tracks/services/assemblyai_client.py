import logging
from typing import Dict, Any
from uuid import UUID

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
)
from application.karaoke_tracks.services.assemblyai_exceptions import (
    AssemblyAISubmitError,
    AssemblyAIGetError,
    AssemblyAITranscriptionError,
)

logger = logging.getLogger(__name__)


class IAssemblyAIClient:
    """Интерфейс клиента AssemblyAI"""

    async def submit_transcription(
        self, audio_url: str, language_code: str, task_id: UUID
    ) -> SubmitTranscriptResponseWithContext:
        """Создает транскрипцию и возвращает ID с контекстом"""
        pass

    async def get_transcription(
        self, transcript_id: str
    ) -> GetTranscriptResponseWithContext:
        """Получает транскрипцию по ID с контекстом"""
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
                punctuate=True,
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
