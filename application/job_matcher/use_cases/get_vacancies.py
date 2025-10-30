import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import aliased

from application.job_matcher.models import (
    JobMatcherVacancy,
    JobMatcherVacancyWithResumeMatch,
    SpecialistType,
    Grade,
    WorkFormat,
)
from core.database.uow import UoW
from sqlalchemy import select, desc, or_, and_, func


class GetVacanciesFilter(BaseModel):
    specialist_type: Optional[SpecialistType]
    grade: Optional[Grade]
    work_format: Optional[WorkFormat]
    with_duplicates: Optional[bool]
    query_text: Optional[str]


class VacancyWithCounts(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    vacancy: JobMatcherVacancy
    duplicates_count: int = 0
    recommended_matches_count: int = 0
    not_recommended_matches_count: int = 0


async def get_vacancies(
    query_filters: GetVacanciesFilter,
    limit: int,
    last_vacancy_id: Optional[uuid.UUID],
    uow: UoW,
) -> List[VacancyWithCounts]:
    async with uow:
        # Создаем алиас для таблицы дубликатов
        DuplicateVacancy = aliased(JobMatcherVacancy)

        filters = [JobMatcherVacancy.processed_at.is_not(None)]
        if query_filters.specialist_type:
            filters.append(
                JobMatcherVacancy.specialist_type == query_filters.specialist_type
            )
        if query_filters.grade:
            filters.append(JobMatcherVacancy.grade == query_filters.grade)
        if query_filters.work_format:
            filters.append(JobMatcherVacancy.work_format == query_filters.work_format)
        if query_filters.query_text:
            filters.append(
                JobMatcherVacancy.text.ilike(f"%{query_filters.query_text}%")
            )
        if not query_filters.with_duplicates:
            filters.append(JobMatcherVacancy.original_vacancy_id.is_(None))

        # Подзапрос для подсчета количества дубликатов (исправленный)
        duplicates_count_subquery = (
            select(func.count(DuplicateVacancy.id))
            .where(DuplicateVacancy.original_vacancy_id == JobMatcherVacancy.id)
            .scalar_subquery()
        )

        # Подзапросы для подсчета количества сопоставлений
        recommended_matches_count_subquery = (
            select(func.count(JobMatcherVacancyWithResumeMatch.id))
            .where(
                JobMatcherVacancyWithResumeMatch.vacancy_id == JobMatcherVacancy.id,
                JobMatcherVacancyWithResumeMatch.is_recommended.is_(True),
            )
            .scalar_subquery()
        )

        not_recommended_matches_count_subquery = (
            select(func.count(JobMatcherVacancyWithResumeMatch.id))
            .where(
                JobMatcherVacancyWithResumeMatch.vacancy_id == JobMatcherVacancy.id,
                JobMatcherVacancyWithResumeMatch.is_recommended.is_(False),
            )
            .scalar_subquery()
        )

        # Основной запрос
        query = (
            select(
                JobMatcherVacancy,
                duplicates_count_subquery.label("duplicates_count"),
                recommended_matches_count_subquery.label("recommended_matches_count"),
                not_recommended_matches_count_subquery.label(
                    "not_recommended_matches_count"
                ),
            )
            .order_by(desc(JobMatcherVacancy.created_at), desc(JobMatcherVacancy.id))
            .filter(*filters)
        )

        # Пагинация
        if last_vacancy_id:
            last_vacancy = (
                await uow.session.execute(
                    select(JobMatcherVacancy).where(
                        JobMatcherVacancy.id == last_vacancy_id
                    )
                )
            ).scalar_one_or_none()
            if last_vacancy:
                query = query.filter(
                    or_(
                        JobMatcherVacancy.created_at < last_vacancy.created_at,
                        and_(
                            JobMatcherVacancy.created_at == last_vacancy.created_at,
                            JobMatcherVacancy.id < last_vacancy.id,
                        ),
                    )
                )

        # Выполняем запрос
        result = await uow.session.execute(query.limit(limit))

        # Формируем результат
        vacancies_with_counts = []
        for row in result:
            vacancy_with_counts = VacancyWithCounts(
                vacancy=row.JobMatcherVacancy,
                duplicates_count=row.duplicates_count or 0,
                recommended_matches_count=row.recommended_matches_count or 0,
                not_recommended_matches_count=row.not_recommended_matches_count or 0,
            )
            vacancies_with_counts.append(vacancy_with_counts)

        return vacancies_with_counts
