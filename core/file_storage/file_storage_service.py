import uuid
from typing import Optional

import aiohttp
import aioboto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, validator

from core.errors import BaseError


class FileStorageConfig(BaseModel):
    """Конфигурация для S3 хранилища"""

    endpoint_url: str = Field(..., description="URL эндпоинта S3")
    access_key_id: str = Field(..., description="Ключ доступа")
    secret_access_key: str = Field(..., description="Секретный ключ")
    bucket_name: str = Field(..., description="Имя бакета")
    region: str = Field(default="us-east-1", description="Регион")
    secure: bool = Field(default=False, description="Использовать SSL")

    @validator("endpoint_url")
    def validate_endpoint_url(cls, v):
        """Валидация URL эндпоинта"""
        if not v:
            raise ValueError("Endpoint URL cannot be empty")
        return v

    @validator("bucket_name")
    def validate_bucket_name(cls, v):
        """Валидация имени бакета"""
        if not v:
            raise ValueError("Bucket name cannot be empty")
        # S3 bucket naming rules
        if len(v) < 3 or len(v) > 63:
            raise ValueError("Bucket name must be between 3 and 63 characters")
        return v

    class Config:
        frozen = True  # Делаем конфиг неизменяемым после создания


class FileStorageError(BaseError):
    code: str = "file_storage_error"
    message: str = "File storage error"


class FileNotFoundError(FileStorageError):
    code: str = "file_not_found"
    message: str = "File not found"


class FileUploadError(FileStorageError):
    code: str = "file_upload_error"
    message: str = "File upload error"


class FileStorageService:
    def __init__(self, config: FileStorageConfig):
        self.config = config
        self.session: Optional[aioboto3.Session] = None

    async def _get_session(self) -> aioboto3.Session:
        if self.session is None:
            self.session = aioboto3.Session()
        return self.session

    async def _get_client(self):
        session = await self._get_session()
        return session.client(
            "s3",
            endpoint_url=self.config.endpoint_url,
            aws_access_key_id=self.config.access_key_id,
            aws_secret_access_key=self.config.secret_access_key,
            region_name=self.config.region,
            verify=self.config.secure,
        )

    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Загружает файл в S3 и возвращает его ключ"""
        try:
            file_key = f"{uuid.uuid4()}_{file_name}"

            async with await self._get_client() as client:
                await client.put_object(
                    Bucket=self.config.bucket_name,
                    Key=file_key,
                    Body=file_content,
                    ContentType=content_type,
                )

            return file_key
        except ClientError as e:
            raise FileUploadError(details=str(e))
        except Exception as e:
            raise FileStorageError(details=str(e))

    async def upload_file_from_url(
        self, url: str, file_name: Optional[str] = None
    ) -> str:
        """Загружает файл по URL в S3 и возвращает его ключ"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise FileUploadError(
                            details=f"Failed to download file from URL: {response.status}"
                        )

                    file_content = await response.read()
                    content_type = response.headers.get(
                        "Content-Type", "application/octet-stream"
                    )

                    if not file_name:
                        # Извлекаем имя файла из URL или генерируем
                        file_name = url.split("/")[-1] or f"downloaded_{uuid.uuid4()}"

                    return await self.upload_file(file_content, file_name, content_type)

        except aiohttp.ClientError as e:
            raise FileUploadError(details=f"HTTP error: {str(e)}")
        except Exception as e:
            raise FileStorageError(details=str(e))

    async def download_file(self, file_key: str) -> bytes:
        """Скачивает файл из S3 по ключу"""
        try:
            async with await self._get_client() as client:
                response = await client.get_object(
                    Bucket=self.config.bucket_name, Key=file_key
                )

                async with response["Body"] as stream:
                    return await stream.read()

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey":
                raise FileNotFoundError(details=f"File with key {file_key} not found")
            raise FileStorageError(details=str(e))
        except Exception as e:
            raise FileStorageError(details=str(e))

    async def get_file_url(self, file_key: str, expires_in: int = 3600) -> str:
        """Генерирует временную ссылку для доступа к файлу"""
        try:
            async with await self._get_client() as client:
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.config.bucket_name, "Key": file_key},
                    ExpiresIn=expires_in,
                )
                return url
        except ClientError as e:
            raise FileStorageError(details=str(e))

    async def delete_file(self, file_key: str) -> bool:
        """Удаляет файл из S3"""
        try:
            async with await self._get_client() as client:
                await client.delete_object(Bucket=self.config.bucket_name, Key=file_key)
                return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey":
                raise FileNotFoundError(details=f"File with key {file_key} not found")
            raise FileStorageError(details=str(e))
        except Exception as e:
            raise FileStorageError(details=str(e))

    async def file_exists(self, file_key: str) -> bool:
        """Проверяет существование файла в S3"""
        try:
            async with await self._get_client() as client:
                await client.head_object(Bucket=self.config.bucket_name, Key=file_key)
                return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey" or error_code == "404":
                return False
            raise FileStorageError(details=str(e))
        except Exception as e:
            raise FileStorageError(details=str(e))
