from application.job_matcher.use_cases.activate_resume import activate_resume
from application.job_matcher.use_cases.add_manual_resume import add_manual_resume
from application.job_matcher.use_cases.add_manual_vacancy import add_manual_vacancy
from application.job_matcher.use_cases.deactivate_resume import deactivate_resume
from application.job_matcher.use_cases.get_resumes import get_resumes, GetResumesFilter
from application.job_matcher.use_cases.get_resume_by_id import get_resume_by_id
from application.job_matcher.use_cases.get_statistics import (
    get_statistics,
    StatisticsResult,
)
from application.job_matcher.use_cases.get_vacancies import (
    get_vacancies,
    GetVacanciesFilter,
    VacancyWithCounts,
)
from application.job_matcher.use_cases.get_vacancy_by_id import get_vacancy_by_id

from application.job_matcher.use_cases.match_vacancies_with_resumes import (
    match_vacancies_with_resumes,
)
from application.job_matcher.use_cases.check_vacancies_for_duplicates import (
    check_vacancies_for_duplicates,
)

__all__ = [
    "activate_resume",
    "deactivate_resume",
    "add_manual_resume",
    "add_manual_vacancy",
    "get_resumes",
    "get_resume_by_id",
    "GetResumesFilter",
    "get_statistics",
    "StatisticsResult",
    "get_vacancies",
    "GetVacanciesFilter",
    "VacancyWithCounts",
    "get_vacancy_by_id",
    "match_vacancies_with_resumes",
    "check_vacancies_for_duplicates",
]
