import dataclasses
import uuid
from typing import Optional

from pydantic import BaseModel

from application.job_matcher.models import (
    SourceType,
    JobMatcherVacancy,
    SpecialistType,
    WorkFormat,
    Grade,
    Technology,
    Skill,
    Salary,
)
from application.job_matcher.services import LLMService, GetVacancyResult


class DataForVacancyCollection(BaseModel):
    vacancy_text: str
    source_type: SourceType
    source_id: Optional[uuid.UUID] = None


@dataclasses.dataclass
class VacancyCollectionResult:
    vacancy: JobMatcherVacancy
    get_vacancy_result: GetVacancyResult


class CollectVacancyError(Exception):
    message: str = "Invalid vacancy text"
    get_vacancy_result: GetVacancyResult

    def __init__(
        self,
        get_vacancy_result: GetVacancyResult,
    ):
        self.get_vacancy_result = get_vacancy_result
        super().__init__(self.message)


class VacancyCollector:
    llm_service: LLMService

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def collect_vacancy(
        self, data: DataForVacancyCollection
    ) -> VacancyCollectionResult:
        result = await self.llm_service.try_get_vacancy_from_text(data.vacancy_text)
        if not result.is_vacancy:
            raise CollectVacancyError(
                get_vacancy_result=result,
            )

        return VacancyCollectionResult(
            vacancy=JobMatcherVacancy(
                source_type=data.source_type,
                source_id=data.source_id,
                text=data.vacancy_text,
                company=result.vacancy.company,
                job_title=result.vacancy.job_title,
                specialist_type=SpecialistType(result.vacancy.specialist_type.value),
                work_format=WorkFormat(result.vacancy.work_format.value),
                grade=Grade(result.vacancy.grade.value),
                experience_required=result.vacancy.experience_required,
                salary=Salary(
                    salary_from=result.vacancy.salary.salary_from,
                    salary_to=result.vacancy.salary.salary_to,
                    currency=result.vacancy.salary.currency,
                    tax_included=result.vacancy.salary.tax_included,
                )
                if result.vacancy.salary.is_defined
                else None,
                technologies=[
                    Technology(
                        name=el.name,
                        level=el.level,
                        required=el.required,
                    )
                    for el in result.vacancy.technologies
                ],
                skills=[
                    Skill(
                        name=el.name,
                        level=el.level,
                        required=el.required,
                    )
                    for el in result.vacancy.skills
                ],
                duplicate_checked_at=None,
                duplicate_check_success=None,
                original_vacancy_id=None,
            ),
            get_vacancy_result=result,
        )
