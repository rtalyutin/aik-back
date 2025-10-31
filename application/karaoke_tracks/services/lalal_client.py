import uuid
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from pydantic import BaseModel


class VocalInstrumentalSeparationResult(BaseModel):
    success: bool
    vocal_file_url: Optional[str] = None
    instrumental_file_url: Optional[str] = None
    error_message: Optional[str] = None


class ILalalClient(ABC):
    @abstractmethod
    async def separate_track(
        self, audio_file_url: str, task_id: uuid.UUID
    ) -> VocalInstrumentalSeparationResult:
        pass


class LalalClient(ILalalClient):
    def __init__(self, api_key: str, base_url: str = "https://api.lalal.ai/v1"):
        self.api_key = api_key
        self.base_url = base_url

    async def separate_track(
        self, audio_file_url: str, task_id: uuid.UUID
    ) -> VocalInstrumentalSeparationResult:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/clean/",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"audio": await self._download_file(audio_file_url)},
                    data={"split_type": "vocal_instrumental"},
                )

                if response.status_code == 200:
                    data = response.json()
                    return VocalInstrumentalSeparationResult(
                        success=True,
                        vocal_file_url=data.get("vocal_url"),
                        instrumental_file_url=data.get("instrumental_url"),
                    )
                else:
                    return VocalInstrumentalSeparationResult(
                        success=False,
                        error_message=f"API error: {response.status_code}",
                    )

        except Exception as e:
            return VocalInstrumentalSeparationResult(
                success=False, error_message=str(e)
            )

    async def _download_file(self, url: str) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
