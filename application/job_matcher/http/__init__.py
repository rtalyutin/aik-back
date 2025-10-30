from application.job_matcher.http.resume_router import (
    router as job_matcher_resume_router,
)
from application.job_matcher.http.statistics_router import (
    router as job_matcher_statistic_router,
)
from application.job_matcher.http.vacancy_router import (
    router as job_matcher_vacancy_router,
)

__all__ = [
    job_matcher_resume_router,
    job_matcher_statistic_router,
    job_matcher_vacancy_router,
]
