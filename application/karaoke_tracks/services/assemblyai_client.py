import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

import httpx
from pydantic import BaseModel


class TranscriptResult(BaseModel):
    success: bool
    transcript: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class IAssemblyAIClient(ABC):
    @abstractmethod
    async def transcribe_audio(
        self, audio_file_url: str, language_code: str, task_id: uuid.UUID
    ) -> TranscriptResult:
        pass


class AssemblyAIClient(IAssemblyAIClient):
    def __init__(self, api_key: str, base_url: str = "https://api.assemblyai.com/v2"):
        self.api_key = api_key
        self.base_url = base_url

    async def transcribe_audio(
        self, audio_file_url: str, language_code: str, task_id: uuid.UUID
    ) -> TranscriptResult:
        try:
            async with httpx.AsyncClient() as client:
                # Начинаем транскрипцию
                transcript_response = await client.post(
                    f"{self.base_url}/transcript",
                    headers={"Authorization": self.api_key},
                    json={
                        "audio_url": audio_file_url,
                        "language_code": language_code,
                        "speaker_labels": True,
                    },
                )

                if transcript_response.status_code == 200:
                    transcript_id = transcript_response.json()["id"]

                    # Ожидаем завершения транскрипции
                    transcript_data = await self._wait_for_transcription(
                        client, transcript_id
                    )

                    if transcript_data:
                        return TranscriptResult(
                            success=True, transcript=transcript_data
                        )
                    else:
                        return TranscriptResult(
                            success=False, error_message="Transcription timeout"
                        )
                else:
                    return TranscriptResult(
                        success=False,
                        error_message=f"API error: {transcript_response.status_code}",
                    )

        except Exception as e:
            return TranscriptResult(success=False, error_message=str(e))

    async def _wait_for_transcription(
        self, client, transcript_id: str, timeout: int = 300
    ) -> Optional[Dict[str, Any]]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = await client.get(
                f"{self.base_url}/transcript/{transcript_id}",
                headers={"Authorization": self.api_key},
            )

            if response.status_code == 200:
                data = response.json()
                status = data.get("status")

                if status == "completed":
                    return data
                elif status in ("failed", "error"):
                    return None

            await asyncio.sleep(5)

        return None
