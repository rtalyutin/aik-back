from uuid import UUID

from core.errors import BaseError


class ResumeNotFoundException(BaseError):
    status_code = 404
    code: str = "resume_not_found"
    resume_id: UUID

    def __init__(self, resume_id: UUID):
        self.resume_id = resume_id
        super().__init__(message=f"Resume with ID {str(resume_id)} not found")


class ResumeAlreadyActivatedException(BaseError):
    code: str = "resume_already_activated"
    resume_id: UUID

    def __init__(self, resume_id: UUID):
        self.resume_id = resume_id
        super().__init__(message="Resume with ID {str(resume_id)} already activated")


class ResumeAlreadyNotActivatedException(BaseError):
    code: str = "resume_already_not_activated"
    resume_id: UUID

    def __init__(self, resume_id: UUID):
        self.resume_id = resume_id
        super().__init__(
            message="Resume with ID {str(resume_id)} already not activated"
        )


class VacancyNotFoundException(BaseError):
    status_code = 404
    code: str = "vacancy_not_found"
    vacancy_id: UUID

    def __init__(self, vacancy_id: UUID):
        self.vacancy_id = vacancy_id
        super().__init__(message=f"Vacancy with ID {str(vacancy_id)} not found")
