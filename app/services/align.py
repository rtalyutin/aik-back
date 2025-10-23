"""Alignment provider abstraction."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AlignmentLine:
    """Single line in the enhanced LRC output."""

    start: float
    end: float
    text: str

    def to_lrc(self) -> str:
        minutes, seconds = divmod(self.start, 60)
        return f"[{int(minutes):02d}:{seconds:05.2f}]{self.text}"


@dataclass(slots=True)
class AlignmentResult:
    """Represents alignment output."""

    lines: list[AlignmentLine]

    def to_lrc(self) -> str:
        return "\n".join(line.to_lrc() for line in self.lines)


class AlignService:
    """Simulated ALIGN provider."""

    def __init__(self, provider: str) -> None:
        self.provider = provider

    async def align(self, words: list[dict[str, float | str]]) -> AlignmentResult:
        """Align ASR words to produce Enhanced LRC."""

        await asyncio.sleep(0.05)
        lines: list[AlignmentLine] = []
        buffer: list[str] = []
        start: float | None = None
        end: float | None = None
        for token in words:
            word = str(token.get("word", "")).strip()
            if not word:
                continue
            if start is None:
                start = float(token.get("start", 0.0))
            end = float(token.get("end", 0.0))
            buffer.append(word)
            if word.endswith(('.', '!', '?')):
                lines.append(AlignmentLine(start=start, end=end, text=" ".join(buffer)))
                buffer = []
                start = None
        if buffer:
            lines.append(AlignmentLine(start=start or 0.0, end=end or 0.0, text=" ".join(buffer)))
        logger.info("Generated %s alignment lines", len(lines))
        return AlignmentResult(lines=lines)
