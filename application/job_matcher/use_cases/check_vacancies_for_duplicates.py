import datetime
import logging
from typing import Dict, Any, Optional
import uuid

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select

from application.job_matcher.services import LLMService
from application.job_matcher.services.llm_service import CheckVacancyDuplicateError
from application.job_matcher.models import (
    JobMatcherVacancy,
    JobMatcherVacancyDuplicateCheckProcessLog,
)
from config import get_config

logger = logging.getLogger(__name__)


class DuplicateCheckResult(BaseModel):
    """Результат проверки вакансии на дубликат"""

    has_error: bool
    is_duplicate: bool
    similar_vacancy_id: uuid.UUID
    error_data: Optional[Dict[str, Any]] = None
    check_data: Optional[Dict[str, Any]] = None


async def check_vacancies_for_duplicates(
    session_maker: async_sessionmaker[AsyncSession],
    llm_service: LLMService,
) -> None:
    logger.info("Checking vacancies for duplicates start")

    async with session_maker() as session:
        vacancies_to_check = list(
            (
                await session.execute(
                    select(JobMatcherVacancy)
                    .where(JobMatcherVacancy.duplicate_checked_at.is_(None))
                    .order_by(JobMatcherVacancy.created_at, JobMatcherVacancy.id)
                    .limit(20)
                )
            )
            .scalars()
            .all()
        )

    logger.info(f"Found {len(vacancies_to_check)} vacancies to check for duplicates")

    for vacancy in vacancies_to_check:
        await __check_vacancy_for_duplicates(vacancy, session_maker, llm_service)

    logger.info("Checking vacancies for duplicates end")


async def __check_vacancy_for_duplicates(
    vacancy: JobMatcherVacancy,
    session_maker: async_sessionmaker[AsyncSession],
    llm_service: LLMService,
) -> None:
    logger.info(f"Checking vacancy {vacancy.id} for duplicates")

    async with session_maker() as session:
        # Получаем вакансии для сравнения:
        # - уже проверенные на дубли успешно
        # - без дублей (original_vacancy_id is None)
        # - добавленные не более 2 часов назад от создания текущей вакансии
        # - с совпадающими грейдом и специализацией
        two_hours_ago = vacancy.created_at - datetime.timedelta(hours=2)

        similar_vacancies = list(
            (
                await session.execute(
                    select(JobMatcherVacancy)
                    .where(JobMatcherVacancy.duplicate_checked_at.is_not(None))
                    .where(JobMatcherVacancy.duplicate_check_success.is_(True))
                    .where(JobMatcherVacancy.original_vacancy_id.is_(None))
                    .where(JobMatcherVacancy.created_at >= two_hours_ago)
                    .where(JobMatcherVacancy.created_at < vacancy.created_at)
                    .where(JobMatcherVacancy.grade == vacancy.grade)
                    .where(JobMatcherVacancy.specialist_type == vacancy.specialist_type)
                    .where(JobMatcherVacancy.id != vacancy.id)
                    .order_by(JobMatcherVacancy.created_at.asc())
                )
            )
            .scalars()
            .all()
        )

    logger.info(
        f"Found {len(similar_vacancies)} similar vacancies to compare for vacancy {vacancy.id}"
    )

    if not similar_vacancies:
        # Если похожих вакансий не найдено, отмечаем проверку завершенной успешно
        await __mark_vacancy_as_unique(vacancy, session_maker)
        logger.info(
            f"No similar vacancies found for vacancy {vacancy.id}, marked as checked and unique"
        )
        return

    # Проверяем каждую похожую вакансию от самой старой к самой новой
    for similar_vacancy in similar_vacancies:
        check_result = await __check_if_duplicate(vacancy, similar_vacancy, llm_service)

        if check_result.has_error:
            # Произошла ошибка при проверке - прерываем обработку
            await __mark_vacancy_check_failed(vacancy, check_result, session_maker)
            logger.error(
                f"Failed to check vacancy {vacancy.id} for duplicates due to LLM error"
            )
            return

        if check_result.is_duplicate:
            # Вакансия является дублем - прерываем обработку
            await __mark_vacancy_as_duplicate(
                vacancy, similar_vacancy, check_result, session_maker
            )
            logger.info(
                f"Vacancy {vacancy.id} is a duplicate of vacancy {similar_vacancy.id}"
            )
            return

    # Если дублей не найдено, отмечаем проверку завершенной успешно
    await __mark_vacancy_as_unique(vacancy, session_maker)
    logger.info(
        f"No duplicates found for vacancy {vacancy.id}, marked as checked and unique"
    )


async def __check_if_duplicate(
    vacancy: JobMatcherVacancy,
    similar_vacancy: JobMatcherVacancy,
    llm_service: LLMService,
) -> DuplicateCheckResult:
    """
    Проверяет, является ли вакансия дубликатом.

    Returns:
        DuplicateCheckResult с информацией о результате проверки
    """
    logger.info(f"Comparing vacancy {vacancy.id} with vacancy {similar_vacancy.id}")

    try:
        result = await llm_service.check_vacancy_duplicate(
            vacancy.text, similar_vacancy.text
        )
    except (CheckVacancyDuplicateError, Exception) as exception:
        logger.exception(
            f"Failed to check vacancy {vacancy.id} for duplicate with {similar_vacancy.id}",
            exc_info=exception,
        )

        error_data: Dict[str, Any] = {
            "exception": str(exception),
            "exception_type": type(exception).__name__,
        }
        if isinstance(exception, CheckVacancyDuplicateError):
            error_data["metainfo"] = exception.metainfo

        return DuplicateCheckResult(
            has_error=True,
            is_duplicate=False,
            similar_vacancy_id=similar_vacancy.id,
            error_data=error_data,
        )

    min_score = get_config().JOB_MATCHER_MIN_SCORE_FOR_DUPLICATE

    logger.info(
        f"Duplicate check result for vacancy {vacancy.id} with {similar_vacancy.id}: "
        f"score={result.probability_score}, threshold={min_score}"
    )

    is_duplicate = result.probability_score >= min_score

    check_data: Dict[str, Any] = {
        "probability_score": result.probability_score,
        "threshold": min_score,
        "metainfo": result.metainfo,
    }

    return DuplicateCheckResult(
        has_error=False,
        is_duplicate=is_duplicate,
        similar_vacancy_id=similar_vacancy.id,
        check_data=check_data,
    )


async def __mark_vacancy_as_duplicate(
    vacancy: JobMatcherVacancy,
    original_vacancy: JobMatcherVacancy,
    check_result: DuplicateCheckResult,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Отмечает вакансию как дубликат"""
    async with session_maker() as session:
        vacancy.duplicate_checked_at = datetime.datetime.now(datetime.UTC)
        vacancy.duplicate_check_success = True
        vacancy.original_vacancy_id = original_vacancy.id
        session.add(vacancy)

        log = JobMatcherVacancyDuplicateCheckProcessLog(
            vacancy_id=vacancy.id,
            is_duplicate=True,
            duplicate_of_vacancy_id=original_vacancy.id,
            data=check_result.check_data or {},
        )
        session.add(log)
        await session.commit()

    logger.info(
        f"Vacancy {vacancy.id} marked as duplicate of vacancy {original_vacancy.id}"
    )


async def __mark_vacancy_as_unique(
    vacancy: JobMatcherVacancy,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Отмечает вакансию как уникальную (не дубликат)"""
    async with session_maker() as session:
        vacancy.duplicate_checked_at = datetime.datetime.now(datetime.UTC)
        vacancy.duplicate_check_success = True
        session.add(vacancy)

        log = JobMatcherVacancyDuplicateCheckProcessLog(
            vacancy_id=vacancy.id,
            is_duplicate=False,
            duplicate_of_vacancy_id=None,
            data={"result": "no_duplicates_found"},
        )
        session.add(log)
        await session.commit()

    logger.info(f"Vacancy {vacancy.id} marked as unique (no duplicates)")


async def __mark_vacancy_check_failed(
    vacancy: JobMatcherVacancy,
    check_result: DuplicateCheckResult,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Отмечает, что проверка вакансии завершилась с ошибкой"""
    async with session_maker() as session:
        vacancy.duplicate_checked_at = datetime.datetime.now(datetime.UTC)
        vacancy.duplicate_check_success = False
        session.add(vacancy)

        log = JobMatcherVacancyDuplicateCheckProcessLog(
            vacancy_id=vacancy.id,
            is_duplicate=None,
            duplicate_of_vacancy_id=check_result.similar_vacancy_id,
            data=check_result.error_data or {},
        )
        session.add(log)
        await session.commit()

    logger.error(
        f"Vacancy {vacancy.id} check failed with error",
        extra={"error_data": check_result.error_data},
    )
