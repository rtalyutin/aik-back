"""ASR provider abstraction."""

from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ASRResult:
    """Represents a finished transcription."""

    transcript: str
    words: list[dict[str, float | str]]


class ASRService:
    """Simulated ASR provider used for orchestrating callbacks."""

    def __init__(self, provider: str, *, callback_secret: str | None = None) -> None:
        self.provider = provider
        self.callback_secret = callback_secret

    async def start_transcription(self, job_id: str, audio_url: str) -> str:
        """Start ASR processing and return tracking identifier."""

        logger.info("Starting ASR for job %s using %s", job_id, self.provider)
        await asyncio.sleep(0.05)
        return secrets.token_hex(8)

    def verify_signature(self, signature: str | None) -> bool:
        """Validate callback signature."""

        if self.callback_secret is None:
            return True
        return secrets.compare_digest(signature or "", self.callback_secret)

    async def build_result(self, transcript: str) -> ASRResult:
        """Construct ASR result with simple word-level timings."""

        await asyncio.sleep(0.01)
        words = []
        current = 0.0
        for token in transcript.split():
            words.append({"word": token, "start": current, "end": current + 0.5})
            current += 0.5
        return ASRResult(transcript=transcript, words=words)
