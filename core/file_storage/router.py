from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import Response
from pydantic import BaseModel, HttpUrl
from typing import Optional
from dishka import FromDishka
from dishka.integrations.fastapi import inject

from core.file_storage.file_storage_service import (
    FileStorageService,
    FileStorageError,
    FileNotFoundError,
    FileUploadError,
)
from core.auth import authentication_middleware
from core.handlers.handlers import get_responses_for_exceptions
from core.responses.responses import BaseDataResponse

router = APIRouter(
    prefix="/file-storage",
    tags=["file-storage"],
    dependencies=[Depends(authentication_middleware)],
)


# ✅ Типизированные модели для запросов
class UploadFileFromUrlRequest(BaseModel):
    url: HttpUrl
    file_name: Optional[str] = None


# ✅ Типизированные модели для ответов
class UploadFileResponseData(BaseModel):
    file_key: str
    file_name: Optional[str]
    content_type: Optional[str]
    size: Optional[int]


class UploadFileFromUrlResponseData(BaseModel):
    file_key: str
    source_url: str
    file_name: Optional[str]


class FileUrlResponseData(BaseModel):
    file_key: str
    url: str
    expires_in: int


class DeleteFileResponseData(BaseModel):
    success: bool
    message: str


# ✅ Типизированные response models
class UploadFileResponse(BaseDataResponse[UploadFileResponseData]):
    pass


class UploadFileFromUrlResponse(BaseDataResponse[UploadFileFromUrlResponseData]):
    pass


class FileUrlResponse(BaseDataResponse[FileUrlResponseData]):
    pass


class DeleteFileResponse(BaseDataResponse[DeleteFileResponseData]):
    pass


@router.post(
    "/upload",
    response_model=UploadFileResponse,
    responses=get_responses_for_exceptions(
        FileUploadError,
        FileStorageError,
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def upload_file(
    file: UploadFile = File(..., description="Файл для загрузки"),
    file_storage_service: FromDishka[FileStorageService] = FromDishka(),
) -> UploadFileResponse:
    """Загрузка файла в S3 хранилище"""
    file_content = await file.read()
    file_key = await file_storage_service.upload_file(
        file_content=file_content,
        file_name=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
    )

    return UploadFileResponse(
        data=UploadFileResponseData(
            file_key=file_key,
            file_name=file.filename,
            content_type=file.content_type,
            size=len(file_content),
        )
    )


@router.post(
    "/upload-from-url",
    response_model=UploadFileFromUrlResponse,
    responses=get_responses_for_exceptions(
        FileUploadError,
        FileStorageError,
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def upload_file_from_url(
    request: UploadFileFromUrlRequest,
    file_storage_service: FromDishka[FileStorageService] = FromDishka(),
) -> UploadFileFromUrlResponse:
    """Загрузка файла в S3 по URL"""
    file_key = await file_storage_service.upload_file_from_url(
        str(request.url), request.file_name
    )

    return UploadFileFromUrlResponse(
        data=UploadFileFromUrlResponseData(
            file_key=file_key,
            source_url=str(request.url),
            file_name=request.file_name,
        )
    )


@router.get(
    "/download/{file_key}",
    responses=get_responses_for_exceptions(
        FileNotFoundError,
        FileStorageError,
        with_validation_error=False,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def download_file(
    file_key: str,
    file_storage_service: FromDishka[FileStorageService] = FromDishka(),
) -> Response:
    """Скачивание файла из S3 по ключу"""
    file_content = await file_storage_service.download_file(file_key)

    return Response(
        content=file_content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_key}"},
    )


@router.get(
    "/url/{file_key}",
    response_model=FileUrlResponse,
    responses=get_responses_for_exceptions(
        FileNotFoundError,
        FileStorageError,
        with_validation_error=False,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def get_file_url(
    file_key: str,
    expires_in: int = 3600,
    file_storage_service: FromDishka[FileStorageService] = FromDishka(),
) -> FileUrlResponse:
    """Получение временной ссылки на файл"""
    url = await file_storage_service.get_file_url(file_key, expires_in)

    return FileUrlResponse(
        data=FileUrlResponseData(
            file_key=file_key,
            url=url,
            expires_in=expires_in,
        )
    )


@router.delete(
    "/{file_key}",
    response_model=DeleteFileResponse,
    responses=get_responses_for_exceptions(
        FileNotFoundError,
        FileStorageError,
        with_validation_error=True,
        with_auth_error=True,
        with_internal_error=True,
    ),
)
@inject
async def delete_file(
    file_key: str,
    file_storage_service: FromDishka[FileStorageService] = FromDishka(),
) -> DeleteFileResponse:
    """Удаление файла из S3"""
    success = await file_storage_service.delete_file(file_key)

    return DeleteFileResponse(
        data=DeleteFileResponseData(
            success=success,
            message=f"File {file_key} deleted successfully",
        )
    )
