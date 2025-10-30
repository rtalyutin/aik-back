from typing import AsyncGenerator, Self

from dishka import Provider, Scope, provide

from core.file_storage.file_storage_service import FileStorageService, FileStorageConfig
from config import get_config


class FileStorageDepsProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_file_storage_config(self: Self) -> FileStorageConfig:
        config = get_config()
        return FileStorageConfig(
            endpoint_url=config.S3_ENDPOINT_URL,
            access_key_id=config.S3_ACCESS_KEY_ID,
            secret_access_key=config.S3_SECRET_ACCESS_KEY,
            bucket_name=config.S3_BUCKET_NAME,
            region=config.S3_REGION,
            secure=config.S3_SECURE,
        )

    @provide(scope=Scope.APP)
    async def get_file_storage_service(
        self: Self, config: FileStorageConfig
    ) -> AsyncGenerator[FileStorageService, None]:
        service = FileStorageService(config)
        yield service
