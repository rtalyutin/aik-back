import enum
import uuid
from typing import Optional, Annotated, List, Dict

from pydantic import BaseModel, Field
from sqlalchemy import UUID, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum
from sqlalchemy.dialects.postgresql import JSONB

from core.models.base import Base
from core.models.fields import (
    uuid_pk,
    PydanticType,
    PydanticListType,
    optional_date_time_tz,
)


class SourceType(str, enum.Enum):
    tg = "tg"
    manual = "manual"


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


class VacancyWithResumeMatchResult(BaseModel):
    score: int = Field(ge=1, le=10, description="Значимость комментария от 1 до 10")
    comments: List["VacancyWithResumeMatchComment"]


class VacancyWithResumeMatchComment(BaseModel):
    text: str = Field(description="Текст комментария")
    score: int = Field(ge=1, le=10, description="Значимость комментария от 1 до 10")


class JobMatcherVacancy(Base):
    __tablename__ = "job_matcher_vacancies"
    id: Mapped[uuid_pk]
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False),
        default=SourceType.manual,
        nullable=False,
    )
    source_id: Mapped[
        Annotated[
            Optional[uuid.UUID],
            mapped_column(UUID(as_uuid=True), nullable=True),
        ]
    ]
    text: Mapped[str]
    company: Mapped[Optional[str]]
    job_title: Mapped[Optional[str]]
    specialist_type: Mapped[SpecialistType] = mapped_column(
        Enum(SpecialistType, native_enum=False),
        default=SpecialistType.other,
        nullable=False,
    )
    work_format: Mapped[WorkFormat] = mapped_column(
        Enum(WorkFormat, native_enum=False),
        default=WorkFormat.office,
        nullable=False,
    )
    grade: Mapped[Grade] = mapped_column(
        Enum(Grade, native_enum=False),
        default=Grade.junior,
        nullable=False,
    )
    experience_required: Mapped[int]
    salary: Mapped[Optional[Salary]] = mapped_column(
        PydanticType(Salary), nullable=True
    )
    technologies: Mapped[List[Technology]] = mapped_column(
        PydanticListType(Technology),
    )
    skills: Mapped[List[Skill]] = mapped_column(
        PydanticListType(Skill),
    )
    processed_at: Mapped[optional_date_time_tz]
    duplicate_checked_at: Mapped[optional_date_time_tz]
    duplicate_check_success: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    original_vacancy_id: Mapped[
        Annotated[
            Optional[uuid.UUID],
            mapped_column(UUID(as_uuid=True), nullable=True),
        ]
    ]

    original_vacancy: Mapped[Optional["JobMatcherVacancy"]] = relationship(
        "JobMatcherVacancy",
        primaryjoin="JobMatcherVacancy.original_vacancy_id == remote(JobMatcherVacancy.id)",
        foreign_keys="[JobMatcherVacancy.original_vacancy_id]",
        back_populates="duplicates",
    )
    duplicates: Mapped[List["JobMatcherVacancy"]] = relationship(
        "JobMatcherVacancy",
        primaryjoin="remote(JobMatcherVacancy.original_vacancy_id) == JobMatcherVacancy.id",
        foreign_keys="[JobMatcherVacancy.original_vacancy_id]",
        back_populates="original_vacancy",
    )
    matches: Mapped[List["JobMatcherVacancyWithResumeMatch"]] = relationship(
        "JobMatcherVacancyWithResumeMatch",
        primaryjoin="JobMatcherVacancy.id == JobMatcherVacancyWithResumeMatch.vacancy_id",
        foreign_keys="[JobMatcherVacancyWithResumeMatch.vacancy_id]",
        back_populates="vacancy",
    )


class JobMatcherSourceProcessLog(Base):
    __tablename__ = "job_matcher_source_process_logs"
    id: Mapped[uuid_pk]
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False),
        default=SourceType.manual,
        nullable=False,
    )
    source_id: Mapped[
        Annotated[
            Optional[uuid.UUID],
            mapped_column(UUID(as_uuid=True), nullable=True),
        ]
    ]
    source_text: Mapped[Optional[str]]
    is_vacancy: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    data: Mapped[Dict] = mapped_column(JSONB, nullable=False)


class JobMatcherResume(Base):
    __tablename__ = "job_matcher_resumes"
    id: Mapped[uuid_pk]
    text: Mapped[str]
    employee: Mapped[Optional[str]]
    specialist_type: Mapped[SpecialistType] = mapped_column(
        Enum(SpecialistType, native_enum=False),
        default=SpecialistType.other,
        nullable=False,
    )
    grade: Mapped[Grade] = mapped_column(
        Enum(Grade, native_enum=False),
        default=Grade.junior,
        nullable=False,
    )
    experience: Mapped[int]
    salary: Mapped[Optional[Salary]] = mapped_column(
        PydanticType(Salary), nullable=True
    )
    technologies: Mapped[List[TechnologyForResume]] = mapped_column(
        PydanticListType(TechnologyForResume),
    )
    skills: Mapped[List[SkillForResume]] = mapped_column(
        PydanticListType(SkillForResume),
    )
    matches: Mapped[List["JobMatcherVacancyWithResumeMatch"]] = relationship(
        "JobMatcherVacancyWithResumeMatch",
        primaryjoin="JobMatcherResume.id == JobMatcherVacancyWithResumeMatch.resume_id",
        foreign_keys="[JobMatcherVacancyWithResumeMatch.resume_id]",
        back_populates="resume",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class JobMatcherVacancyWithResumeMatch(Base):
    __tablename__ = "job_matcher_vacancy_with_resume_matches"
    id: Mapped[uuid_pk]
    vacancy_id: Mapped[
        Annotated[
            uuid.UUID,
            mapped_column(
                UUID(as_uuid=True),
            ),
        ]
    ]
    resume_id: Mapped[
        Annotated[
            uuid.UUID,
            mapped_column(
                UUID(as_uuid=True),
            ),
        ]
    ]
    score: Mapped[int]
    is_recommended: Mapped[bool]
    comments: Mapped[List[VacancyWithResumeMatchComment]] = mapped_column(
        PydanticListType(VacancyWithResumeMatchComment),
    )
    vacancy: Mapped["JobMatcherVacancy"] = relationship(
        primaryjoin="JobMatcherVacancyWithResumeMatch.vacancy_id == JobMatcherVacancy.id",
        foreign_keys="[JobMatcherVacancyWithResumeMatch.vacancy_id]",
        back_populates="matches",
    )
    resume: Mapped["JobMatcherResume"] = relationship(
        primaryjoin="JobMatcherVacancyWithResumeMatch.resume_id == JobMatcherResume.id",
        foreign_keys="[JobMatcherVacancyWithResumeMatch.resume_id]",
        back_populates="matches",
    )


class JobMatcherVacancyWithResumeMatchProcessLog(Base):
    __tablename__ = "job_matcher_vacancy_with_resume_match_process_logs"
    id: Mapped[uuid_pk]
    vacancy_id: Mapped[
        Annotated[
            uuid.UUID,
            mapped_column(
                UUID(as_uuid=True),
            ),
        ]
    ]
    resume_id: Mapped[
        Annotated[
            uuid.UUID,
            mapped_column(
                UUID(as_uuid=True),
            ),
        ]
    ]
    score: Mapped[Optional[int]]
    is_recommended: Mapped[Optional[bool]]
    data: Mapped[Dict] = mapped_column(JSONB, nullable=False)


class JobMatcherVacancyDuplicateCheckProcessLog(Base):
    __tablename__ = "job_matcher_vacancy_duplicate_check_process_logs"
    id: Mapped[uuid_pk]
    vacancy_id: Mapped[
        Annotated[
            uuid.UUID,
            mapped_column(UUID(as_uuid=True), index=True),
        ]
    ]
    is_duplicate: Mapped[Optional[bool]]
    duplicate_of_vacancy_id: Mapped[
        Annotated[
            Optional[uuid.UUID],
            mapped_column(UUID(as_uuid=True), nullable=True),
        ]
    ]
    data: Mapped[Dict] = mapped_column(JSONB, nullable=False)
