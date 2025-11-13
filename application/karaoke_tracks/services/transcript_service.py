import logging
from typing import List

from application.karaoke_tracks.models.models import (
    WordItem,
    SubtitleItem,
    TranscriptItem,
)

logger = logging.getLogger(__name__)


class TranscriptService:
    """Сервис для создания транскрипции из слов и субтитров"""

    @classmethod
    def create_transcript(
        cls, words: List[WordItem], subtitles: List[SubtitleItem]
    ) -> List[TranscriptItem]:
        """
        Создает транскрипцию из слов и субтитров.

        Args:
            words: Список слов с временными метками
            subtitles: Список субтитров с временными метками

        Returns:
            Список элементов транскрипции, где каждый элемент содержит
            текст субтитра и соответствующие ему слова
        """
        if not words or not subtitles:
            logger.warning(
                "Empty words or subtitles provided for transcript creation",
                extra={"words_count": len(words), "subtitles_count": len(subtitles)},
            )
            return []

        # Сортируем слова и субтитры по времени начала
        sorted_words = sorted(words, key=lambda x: x.start)
        sorted_subtitles = sorted(subtitles, key=lambda x: x.start)

        transcript_items = []
        used_words = set()  # Для отслеживания уже использованных слов

        for subtitle in sorted_subtitles:
            # Находим слова, которые заканчиваются в интервале субтитра
            subtitle_words = cls._find_words_for_subtitle(
                sorted_words, subtitle, used_words
            )

            # Корректируем start слов, если они начинаются до начала субтитра
            adjusted_words = cls._adjust_word_starts(subtitle_words, subtitle)

            # Создаем элемент транскрипции
            transcript_item = TranscriptItem(
                text=subtitle.text,
                start=subtitle.start,
                end=subtitle.end,
                words=adjusted_words,
            )

            transcript_items.append(transcript_item)

            # Добавляем использованные слова в множество
            for word in subtitle_words:
                word_id = cls._get_word_id(word)
                used_words.add(word_id)

            logger.debug(
                "Created transcript item",
                extra={
                    "subtitle_text": subtitle.text[:50] + "..."
                    if len(subtitle.text) > 50
                    else subtitle.text,
                    "words_count": len(adjusted_words),
                    "subtitle_start": subtitle.start,
                    "subtitle_end": subtitle.end,
                    "adjusted_words": len(
                        [w for w in adjusted_words if w.start != w.end]
                    ),
                },
            )

        # Валидируем покрытие
        coverage_stats = cls._calculate_coverage(sorted_words, used_words)

        logger.info(
            "Transcript created successfully",
            extra={
                "total_transcript_items": len(transcript_items),
                "total_words": len(words),
                "coverage_stats": coverage_stats,
            },
        )

        return transcript_items

    @classmethod
    def _find_words_for_subtitle(
        cls, sorted_words: List[WordItem], subtitle: SubtitleItem, used_words: set
    ) -> List[WordItem]:
        """
        Находит слова, которые заканчиваются в интервале субтитра.

        Критерий: word.end находится между subtitle.start и subtitle.end
        """
        subtitle_words = []

        for word in sorted_words:
            # Пропускаем уже использованные слова
            word_id = cls._get_word_id(word)
            if word_id in used_words:
                continue

            # Проверяем, заканчивается ли слово в интервале субтитра
            if subtitle.start <= word.end <= subtitle.end:
                subtitle_words.append(word)

        return subtitle_words

    @classmethod
    def _adjust_word_starts(
        cls, words: List[WordItem], subtitle: SubtitleItem
    ) -> List[WordItem]:
        """
        Корректирует start слов, если они начинаются до начала субтитра.

        Если word.start < subtitle.start, то устанавливаем word.start = subtitle.start
        """
        adjusted_words = []

        for word in words:
            # Создаем копию слова для корректировки
            adjusted_word = WordItem(
                text=word.text,
                start=max(word.start, subtitle.start),  # Корректируем start
                end=word.end,
                confidence=word.confidence,
                speaker=word.speaker,
            )
            adjusted_words.append(adjusted_word)

            # Логируем корректировку, если она произошла
            if word.start < subtitle.start:
                logger.debug(
                    "Adjusted word start time",
                    extra={
                        "word_text": word.text,
                        "original_start": word.start,
                        "adjusted_start": adjusted_word.start,
                        "subtitle_start": subtitle.start,
                        "word_end": word.end,
                    },
                )

        return adjusted_words

    @classmethod
    def _get_word_id(cls, word: WordItem) -> str:
        """Создает уникальный идентификатор для слова"""
        return f"{word.text}_{word.start}_{word.end}_{word.speaker or 'unknown'}"

    @classmethod
    def _calculate_coverage(cls, all_words: List[WordItem], used_words: set) -> dict:
        """Рассчитывает статистику покрытия слов"""
        if not all_words:
            return {
                "total_words": 0,
                "matched_words": 0,
                "coverage_percentage": 100.0,
                "unmatched_words": 0,
            }

        total_words = len(all_words)
        matched_count = len(used_words)
        coverage_percentage = (matched_count / total_words) * 100

        # Находим несопоставленные слова для отладки
        unmatched_words = []
        for word in all_words:
            word_id = cls._get_word_id(word)
            if word_id not in used_words:
                unmatched_words.append(
                    {
                        "text": word.text,
                        "start": word.start,
                        "end": word.end,
                        "speaker": word.speaker,
                    }
                )

        stats = {
            "total_words": total_words,
            "matched_words": matched_count,
            "coverage_percentage": round(coverage_percentage, 2),
            "unmatched_words": total_words - matched_count,
            "unmatched_examples": unmatched_words[:5],  # Первые 5 для отладки
        }

        if unmatched_words:
            logger.warning(
                f"Found {len(unmatched_words)} unmatched words",
                extra={"unmatched_examples": unmatched_words[:3]},
            )

        return stats

    @classmethod
    def validate_transcript_timing(cls, transcript: List[TranscriptItem]) -> dict:
        """
        Валидирует временные метки транскрипции.

        Проверяет, что:
        1. Все слова в элементе транскрипции находятся в его временном интервале
        2. Субтитры идут в правильном порядке
        3. Нет пересечений во времени
        """
        if not transcript:
            return {"valid": True, "issues": []}

        issues = []

        # Проверяем порядок субтитров
        for i in range(1, len(transcript)):
            if transcript[i].start < transcript[i - 1].end:
                issues.append(
                    {
                        "type": "overlap",
                        "subtitle1": {
                            "text": transcript[i - 1].text[:50],
                            "start": transcript[i - 1].start,
                            "end": transcript[i - 1].end,
                        },
                        "subtitle2": {
                            "text": transcript[i].text[:50],
                            "start": transcript[i].start,
                            "end": transcript[i].end,
                        },
                    }
                )

        # Проверяем, что слова находятся в пределах субтитров
        for i, item in enumerate(transcript):
            for word in item.words:
                if word.start < item.start:
                    issues.append(
                        {
                            "type": "word_start_before_subtitle",
                            "subtitle_index": i,
                            "subtitle_text": item.text[:50],
                            "word_text": word.text,
                            "word_start": word.start,
                            "subtitle_start": item.start,
                        }
                    )

                if word.end > item.end:
                    issues.append(
                        {
                            "type": "word_end_after_subtitle",
                            "subtitle_index": i,
                            "subtitle_text": item.text[:50],
                            "word_text": word.text,
                            "word_end": word.end,
                            "subtitle_end": item.end,
                        }
                    )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_issues": len(issues),
        }
