from pydantic import BaseModel
from sqlalchemy import func, select, distinct
from core.database.uow import UoW

from application.job_matcher.models import (
    JobMatcherResume,
    JobMatcherVacancy,
    JobMatcherVacancyWithResumeMatch,
)


class StatisticsResult(BaseModel):
    total_resumes: int
    active_resumes: int
    total_vacancies: int
    recommended_vacancies: int
    unprocessed_vacancies: int
    total_matches: int
    recommended_matches: int


async def get_statistics(uow: UoW):
    async with uow:
        # Запрос 1: Статистика по резюме
        resume_query = select(
            func.count(JobMatcherResume.id).label("total_resumes"),
            func.count(JobMatcherResume.id)
            .filter(JobMatcherResume.is_active.is_(True))
            .label("active_resumes"),
        )

        # Запрос 2: Статистика по вакансиям
        total_vacancies_subq = select(
            func.count(JobMatcherVacancy.id)
        ).scalar_subquery()
        recommended_vacancies_subq = (
            select(func.count(distinct(JobMatcherVacancyWithResumeMatch.vacancy_id)))
            .where(JobMatcherVacancyWithResumeMatch.is_recommended.is_(True))
            .scalar_subquery()
        )
        unprocessed_vacancies_subq = (
            select(func.count(JobMatcherVacancy.id))
            .where(JobMatcherVacancy.processed_at.is_(None))
            .scalar_subquery()
        )

        vacancy_query = select(
            total_vacancies_subq.label("total_vacancies"),
            recommended_vacancies_subq.label("recommended_vacancies"),
            unprocessed_vacancies_subq.label("unprocessed_vacancies"),
        )

        # Запрос 3: Статистика по совпадениям
        matches_query = select(
            func.count(JobMatcherVacancyWithResumeMatch.id).label("total_matches"),
            func.count(JobMatcherVacancyWithResumeMatch.id)
            .filter(JobMatcherVacancyWithResumeMatch.is_recommended.is_(True))
            .label("recommended_matches"),
        )

        # Извлекаем результаты
        resume_data = (await uow.session.execute(resume_query)).one()
        vacancy_data = (await uow.session.execute(vacancy_query)).one()
        matches_data = (await uow.session.execute(matches_query)).one()

        return StatisticsResult(
            total_resumes=resume_data.total_resumes,
            active_resumes=resume_data.active_resumes,
            total_vacancies=vacancy_data.total_vacancies,
            recommended_vacancies=vacancy_data.recommended_vacancies,
            unprocessed_vacancies=vacancy_data.unprocessed_vacancies,
            total_matches=matches_data.total_matches,
            recommended_matches=matches_data.recommended_matches,
        )
