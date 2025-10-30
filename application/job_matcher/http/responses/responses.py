import datetime
import uuid
from typing import Optional, List

from pydantic import BaseModel

from application.job_matcher.models import (
    SpecialistType,
    Grade,
    WorkFormat,
    SourceType,
    JobMatcherVacancy,
    JobMatcherResume,
)
from application.job_matcher.use_cases import VacancyWithCounts


class SalaryResponse(BaseModel):
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    currency: str
    tax_included: bool


class TechnologyForResumeResponse(BaseModel):
    name: str
    level: int


class SkillForResumeResponse(BaseModel):
    name: str
    level: int


class CommentResponse(BaseModel):
    text: str
    score: int


# Базовые модели без матчей
class ResumeBaseResponse(BaseModel):
    """Резюме"""

    id: uuid.UUID
    text: str
    employee: Optional[str] = None
    specialist_type: str
    grade: str
    experience: int
    salary: Optional[SalaryResponse] = None
    technologies: List[TechnologyForResumeResponse]
    skills: List[SkillForResumeResponse]
    is_active: bool
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]

    @classmethod
    def make_from_model(cls, model: JobMatcherResume) -> "ResumeBaseResponse":
        return cls(
            id=model.id,
            text=model.text,
            employee=model.employee,
            specialist_type=model.specialist_type,
            grade=model.grade,
            experience=model.experience,
            salary=SalaryResponse(**model.salary.model_dump())
            if model.salary
            else None,
            technologies=[
                TechnologyForResumeResponse(**t.model_dump())
                for t in model.technologies
            ],
            skills=[SkillForResumeResponse(**s.model_dump()) for s in model.skills],
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


# Базовые модели без матчей
class ResumeListItemResponse(BaseModel):
    id: uuid.UUID
    employee: Optional[str] = None
    specialist_type: str
    grade: str
    experience: int
    salary: Optional[SalaryResponse] = None
    is_active: bool
    technologies_count: int
    skills_count: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]

    @classmethod
    def make_from_model(cls, model: JobMatcherResume) -> "ResumeListItemResponse":
        return cls(
            id=model.id,
            employee=model.employee,
            specialist_type=model.specialist_type,
            grade=model.grade,
            experience=model.experience,
            salary=SalaryResponse(**model.salary.model_dump())
            if model.salary
            else None,
            is_active=model.is_active,
            technologies_count=len(model.technologies),
            skills_count=len(model.skills),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class VacancyCommonFieldsResponse(BaseModel):
    """Общие поля для всех моделей вакансий"""

    id: uuid.UUID
    source_type: SourceType
    source_id: Optional[uuid.UUID]
    text: str
    company: Optional[str]
    job_title: Optional[str]
    specialist_type: SpecialistType
    work_format: WorkFormat
    grade: Grade
    experience_required: int
    salary: Optional[SalaryResponse] = None
    technologies: List[TechnologyForResumeResponse]
    skills: List[SkillForResumeResponse]
    created_at: datetime.datetime
    processed_at: datetime.datetime
    updated_at: Optional[datetime.datetime]

    @classmethod
    def _make_common_fields(cls, model: JobMatcherVacancy) -> dict:
        """Создает словарь с общими полями из модели"""
        return {
            "id": model.id,
            "source_type": model.source_type,
            "source_id": model.source_id,
            "text": model.text,
            "company": model.company,
            "job_title": model.job_title,
            "specialist_type": model.specialist_type,
            "work_format": model.work_format,
            "grade": model.grade,
            "experience_required": model.experience_required,
            "salary": SalaryResponse(**model.salary.model_dump())
            if model.salary
            else None,
            "technologies": [
                TechnologyForResumeResponse(**t.model_dump())
                for t in model.technologies
            ],
            "skills": [SkillForResumeResponse(**s.model_dump()) for s in model.skills],
            "created_at": model.created_at,
            "processed_at": model.processed_at,
            "updated_at": model.updated_at,
        }


class VacancyListItemResponse(BaseModel):
    id: uuid.UUID
    source_type: SourceType
    source_id: Optional[uuid.UUID]
    company: Optional[str]
    job_title: Optional[str]
    specialist_type: SpecialistType
    work_format: WorkFormat
    grade: Grade
    experience_required: int
    salary: Optional[SalaryResponse] = None
    original_vacancy_id: Optional[uuid.UUID] = None
    duplicates_count: int
    recommended_matches_count: int
    not_recommended_matches_count: int
    created_at: datetime.datetime
    processed_at: datetime.datetime
    updated_at: Optional[datetime.datetime]

    @classmethod
    def make_from_model(cls, model: VacancyWithCounts) -> "VacancyListItemResponse":
        """Создает словарь с общими полями из модели"""
        return cls(
            id=model.vacancy.id,
            source_type=model.vacancy.source_type,
            source_id=model.vacancy.source_id,
            company=model.vacancy.company,
            job_title=model.vacancy.job_title,
            specialist_type=model.vacancy.specialist_type,
            work_format=model.vacancy.work_format,
            grade=model.vacancy.grade,
            experience_required=model.vacancy.experience_required,
            salary=SalaryResponse(**model.vacancy.salary.model_dump())
            if model.vacancy.salary
            else None,
            original_vacancy_id=model.vacancy.original_vacancy_id,
            duplicates_count=model.duplicates_count,
            recommended_matches_count=model.recommended_matches_count,
            not_recommended_matches_count=model.not_recommended_matches_count,
            created_at=model.vacancy.created_at,
            processed_at=model.vacancy.processed_at,
            updated_at=model.vacancy.updated_at,
        )


class OriginalVacancyResponse(VacancyCommonFieldsResponse):
    """Оригинальная вакансия (без дубликатов для избежания циклической зависимости)"""

    @classmethod
    def make_from_model(cls, model: JobMatcherVacancy) -> "OriginalVacancyResponse":
        return cls(**cls._make_common_fields(model))


class VacancyBaseResponse(VacancyCommonFieldsResponse):
    """Вакансия с дубликатами"""

    original_vacancy: Optional[OriginalVacancyResponse] = None
    duplicates: List["OriginalVacancyResponse"]

    @classmethod
    def make_from_model(cls, model: JobMatcherVacancy) -> "VacancyBaseResponse":
        return cls(
            **cls._make_common_fields(model),
            original_vacancy=OriginalVacancyResponse.make_from_model(
                model.original_vacancy
            )
            if model.original_vacancy
            else None,
            duplicates=[
                OriginalVacancyResponse.make_from_model(duplicate)
                for duplicate in model.duplicates
            ],
        )


# Модели с матчами
class VacancyMatchResponse(BaseModel):
    """Мэтч вакансии"""

    score: int
    is_recommended: bool
    comments: List[CommentResponse]
    vacancy: VacancyBaseResponse


class ResumeMatchResponse(BaseModel):
    """Мэтч резюме"""

    score: int
    is_recommended: bool
    comments: List[CommentResponse]
    resume: ResumeBaseResponse


# Полные модели с матчами
class ResumeResponse(ResumeBaseResponse):
    """Резюме с мэтчем вакансий"""

    not_recommended_matches: List[VacancyMatchResponse] = []
    recommended_matches: List[VacancyMatchResponse] = []

    @classmethod
    def make_from_model(cls, model: JobMatcherResume) -> "ResumeResponse":
        base_data = ResumeBaseResponse.make_from_model(model).model_dump()
        not_recommended_matches = []
        recommended_matches = []

        if hasattr(model, "matches"):
            for job_match in model.matches or []:
                match_resource = VacancyMatchResponse(
                    score=job_match.score,
                    is_recommended=job_match.is_recommended,
                    comments=[
                        CommentResponse(**c.model_dump()) for c in job_match.comments
                    ],
                    vacancy=VacancyBaseResponse.make_from_model(job_match.vacancy),
                )
                if match_resource.is_recommended:
                    recommended_matches.append(match_resource)
                else:
                    not_recommended_matches.append(match_resource)

        return cls(
            **base_data,
            not_recommended_matches=not_recommended_matches,
            recommended_matches=recommended_matches,
        )


class VacancyResponse(VacancyBaseResponse):
    """Вакансия с мэтчем резюме"""

    not_recommended_matches: List[ResumeMatchResponse] = []
    recommended_matches: List[ResumeMatchResponse] = []

    @classmethod
    def make_from_model(cls, model: JobMatcherVacancy) -> "VacancyResponse":
        base_data = VacancyBaseResponse.make_from_model(model).model_dump()
        not_recommended_matches = []
        recommended_matches = []

        if hasattr(model, "matches"):
            for job_match in model.matches or []:
                match_resource = ResumeMatchResponse(
                    score=job_match.score,
                    is_recommended=job_match.is_recommended,
                    comments=[
                        CommentResponse(**c.model_dump()) for c in job_match.comments
                    ],
                    resume=ResumeBaseResponse.make_from_model(job_match.resume),
                )
                if match_resource.is_recommended:
                    recommended_matches.append(match_resource)
                else:
                    not_recommended_matches.append(match_resource)

        return cls(
            **base_data,
            not_recommended_matches=not_recommended_matches,
            recommended_matches=recommended_matches,
        )
