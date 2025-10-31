from uuid import UUID

from core.errors import BaseError


class KaraokeTrackNotFoundException(BaseError):
    status_code = 404
    code: str = "karaoke_track_not_found"
    track_id: UUID

    def __init__(self, track_id: UUID):
        self.track_id = track_id
        super().__init__(message=f"Karaoke track with ID {str(track_id)} not found")


class TrackCreatingTaskNotFoundException(BaseError):
    status_code = 404
    code: str = "track_creating_task_not_found"
    task_id: UUID

    def __init__(self, task_id: UUID):
        self.task_id = task_id
        super().__init__(
            message=f"Track creating task with ID {str(task_id)} not found"
        )


class InvalidFileOrUrlError(BaseError):
    status_code = 400
    code: str = "invalid_file_or_url"
    message: str = "Either file or file_url must be provided, but not both"


class FileProcessingError(BaseError):
    status_code = 400
    code: str = "file_processing_error"
    message: str = "Error processing file"


class ExternalServiceError(BaseError):
    status_code = 502
    code: str = "external_service_error"
    message: str = "Error calling external service"
