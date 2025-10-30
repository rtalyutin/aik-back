from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import enum

from pydantic import BaseModel, Field


class SpecialistType(str, enum.Enum):
    frontend = "frontend"
    backend = "backend"
    fullstack = "fullstack"
    analyst = "analyst"
    devops = "devops"
    qa = "qa"
    authomatic_qa = "authomatic_qa"
    designer = "designer"
    other = "other"


class WorkFormat(str, enum.Enum):
    office = "office"
    remote = "remote"
    hybrid = "hybrid"


class Grade(str, enum.Enum):
    junior = "junior"
    middle = "middle"
    senior = "senior"
    principle = "principle"
    lead = "lead"


class Salary(BaseModel):
    is_defined: bool = Field(description="Зарплата определена")
    salary_from: Optional[int] = Field(description="Минимальная сумма")
    salary_to: Optional[int] = Field(description="Максимальная сумма")
    currency: str = Field(description="ISO код валюты")
    tax_included: bool = Field(description="Признак того, что налоги включены в суммы")


class Technology(BaseModel):
    name: str = Field(description="Наименование технологии")
    level: int = Field(
        ge=1, le=10, description="Уровень технологии по шкале от 1 до 10"
    )
    required: bool = Field(description="Признак обязательного владения технологией")


class Skill(BaseModel):
    name: str = Field(description="Наименование навыка")
    level: int = Field(ge=1, le=10, description="Уровень навыка по шкале от 1 до 10")
    required: bool = Field(description="Признак обязательного владения навыком")


class TechnologyForResume(BaseModel):
    name: str = Field(description="Наименование технологии")
    level: int = Field(
        ge=1, le=10, description="Уровень технологии по шкале от 1 до 10"
    )


class SkillForResume(BaseModel):
    name: str = Field(description="Наименование навыка")
    level: int = Field(ge=1, le=10, description="Уровень навыка по шкале от 1 до 10")


class VacancyData(BaseModel):
    company: Optional[str] = Field(description="Наименование компании")
    job_title: Optional[str] = Field(description="Наименование вакансии")
    specialist_type: SpecialistType = Field(description="Тип IT специалиста")
    work_format: WorkFormat = Field(description="Формат работы")
    grade: Grade = Field(description="Уровень IT специалиста")
    experience_required: int = Field(description="Минимальный опыт в годах")
    salary: Optional[Salary] = Field(description="Информация о зарплате")
    technologies: List[Technology] = Field(description="Список необходимых технологий")
    skills: List[Skill] = Field(description="Список необходимых навыков и софт скилов")


class GetVacancyResult(BaseModel):
    is_vacancy: bool
    vacancy: Optional[VacancyData]
    metainfo: Optional[Dict] = None


class GetVacancyError(Exception):
    message: str = "Failed to get vacancy from text"
    metainfo: Optional[Dict] = None

    def __init__(
        self,
        metainfo: Optional[Dict] = None,
    ):
        self.metainfo = metainfo


class ResumeData(BaseModel):
    employee: Optional[str] = Field(description="Имя сотрудника")
    specialist_type: SpecialistType = Field(description="Тип IT специалиста")
    grade: Grade = Field(description="Уровень IT специалиста")
    experience: int = Field(description="Опыт в годах")
    salary: Optional[Salary] = Field(description="Информация о зарплате")
    technologies: List[TechnologyForResume] = Field(description="Список технологий")
    skills: List[SkillForResume] = Field(description="Список навыков и софт скилов")


class GetResumeResult(BaseModel):
    is_resume: bool
    resume: Optional[ResumeData]
    metainfo: Optional[Dict] = None


class GetResumeError(Exception):
    message: str = "Failed to get resume from text"
    metainfo: Optional[Dict] = None

    def __init__(
        self,
        metainfo: Optional[Dict] = None,
    ):
        self.metainfo = metainfo


class MatchVacancyAndResumeComment(BaseModel):
    text: str
    score: int = Field(ge=1, le=10)


class MatchVacancyAndResumeResult(BaseModel):
    score: int = Field(ge=1, le=10)
    comments: List[MatchVacancyAndResumeComment]
    metainfo: Optional[Dict] = None


class MatchVacancyAndResumeError(Exception):
    message: str = "Failed to match vacancy and resume"
    metainfo: Optional[Dict] = None

    def __init__(
        self,
        metainfo: Optional[Dict] = None,
    ):
        self.metainfo = metainfo


class CheckVacancyDuplicateResult(BaseModel):
    probability_score: int = Field(
        ge=1,
        le=10,
        description="Вероятность того, что вакансии являются дублями по шкале от 1 до 10",
    )
    metainfo: Optional[Dict] = None


class CheckVacancyDuplicateError(Exception):
    message: str = "Failed to check vacancy duplicate"
    metainfo: Optional[Dict] = None

    def __init__(
        self,
        metainfo: Optional[Dict] = None,
    ):
        self.metainfo = metainfo


class LLMService(ABC):
    @abstractmethod
    async def try_get_vacancy_from_text(self, text: str) -> GetVacancyResult:
        pass

    @abstractmethod
    async def try_get_resume_from_text(self, text: str) -> GetResumeResult:
        pass

    @abstractmethod
    async def try_match_vacancy_and_resume(
        self, vacancy_text: str, resume_text: str
    ) -> MatchVacancyAndResumeResult:
        pass

    @abstractmethod
    async def check_vacancy_duplicate(
        self, vacancy_text_1: str, vacancy_text_2: str
    ) -> CheckVacancyDuplicateResult:
        pass
