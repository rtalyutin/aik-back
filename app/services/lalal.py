"""Service abstraction for LALAL.AI and alternative splitters."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass

from .exceptions import ProviderNotAvailable

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SplitResult:
    """Result of a track split operation."""

    minus_key: str
    vocals_key: str
    metrics: dict[str, float]


class LalalService:
    """Interact with LALAL.AI like API or simulate using feature flags."""

    def __init__(
        self,
        *,
        base_url: str | None,
        api_key: str | None,
        use_alternative: bool = False,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.use_alternative = use_alternative

    async def split(self, job_id: str, filename: str) -> SplitResult:
        """Launch split processing for the provided job."""

        if self.use_alternative and not self.base_url:
            raise ProviderNotAvailable("Alternative LALAL provider is not configured")

        logger.info("Starting split for job %s", job_id)
        await asyncio.sleep(0.1)
        minus_key = f"jobs/{job_id}/minus.m4a"
        vocals_key = f"jobs/{job_id}/vocals.m4a"
        metrics = {"processing_time": random.uniform(1, 3), "confidence": 0.95}
        logger.info("Completed split for job %s", job_id)
        return SplitResult(minus_key=minus_key, vocals_key=vocals_key, metrics=metrics)
