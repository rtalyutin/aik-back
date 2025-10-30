from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import Response
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


class UploadFileResponse(BaseDataResponse):
    data: dict


class FileUrlResponse(BaseDataResponse):
    data: dict


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
        data={
            "file_key": file_key,
            "file_name": file.filename,
            "content_type": file.content_type,
            "size": len(file_content),
        }
    )


@router.post(
    "/upload-from-url",
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
async def upload_file_from_url(
    url: str,
    file_name: str = None,
    file_storage_service: FromDishka[FileStorageService] = FromDishka(),
) -> UploadFileResponse:
    """Загрузка файла в S3 по URL"""
    file_key = await file_storage_service.upload_file_from_url(url, file_name)

    return UploadFileResponse(
        data={"file_key": file_key, "source_url": url, "file_name": file_name}
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
        data={"file_key": file_key, "url": url, "expires_in": expires_in}
    )


@router.delete(
    "/{file_key}",
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
) -> BaseDataResponse:
    """Удаление файла из S3"""
    success = await file_storage_service.delete_file(file_key)

    return BaseDataResponse(
        data={
            "success": success,
            "message": f"File {file_key} deleted successfully",
        }
    )
