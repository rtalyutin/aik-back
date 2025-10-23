"""Timeweb S3 integration utilities."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PresignedUpload:
    """Descriptor for uploading an object using a presigned form."""

    url: str
    fields: dict[str, str]
    expires_in: int


@dataclass(slots=True)
class S3ObjectDescriptor:
    """Descriptor returned when object is uploaded or generated."""

    key: str
    url: str


class TimewebS3Service:
    """Generate presigned URLs for a Timeweb S3 compatible storage."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
        region_name: str | None,
        upload_expires: int = 3600,
        use_dummy: bool = False,
    ) -> None:
        self.bucket = bucket
        self.endpoint_url = endpoint_url.rstrip("/") if endpoint_url else None
        self.access_key = access_key or ""
        self.secret_key = secret_key or ""
        self.region_name = region_name or ""
        self.upload_expires = upload_expires
        self.use_dummy = use_dummy or not (self.access_key and self.secret_key)

    def _base_url(self) -> str:
        if self.endpoint_url:
            return f"{self.endpoint_url}/{self.bucket}"
        return f"https://{self.bucket}.s3.{self.region_name or 'timeweb.cloud'}.ru"

    def _generate_key(self, filename: str) -> str:
        sanitized = filename.replace(" ", "_")
        timestamp = int(time.time() * 1000)
        return f"jobs/{timestamp}-{sanitized}"

    def _dummy_presign(self, key: str) -> PresignedUpload:
        url = f"{self._base_url()}/{quote(key)}"
        fields = {"key": key, "AWSAccessKeyId": self.access_key or "dummy"}
        return PresignedUpload(url=url, fields=fields, expires_in=self.upload_expires)

    def generate_presigned_upload(self, filename: str) -> tuple[PresignedUpload, S3ObjectDescriptor]:
        """Create a presigned POST allowing the client to upload the original file."""

        key = self._generate_key(filename)
        if self.use_dummy:
            logger.debug("Using dummy S3 presigned upload for key %s", key)
            upload = self._dummy_presign(key)
        else:
            upload = self._presign_post(key)
        descriptor = S3ObjectDescriptor(key=key, url=f"{self._base_url()}/{quote(key)}")
        logger.info("Generated presigned upload for key %s", key)
        return upload, descriptor

    def generate_presigned_get(self, key: str) -> str:
        """Generate a presigned GET url. Fallback to deterministic URL in dummy mode."""

        if self.use_dummy:
            return f"{self._base_url()}/{quote(key)}"
        expires = int(time.time()) + self.upload_expires
        signature = hmac.new(
            self.secret_key.encode(),
            f"{key}{expires}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"{self._base_url()}/{quote(key)}?AWSAccessKeyId={self.access_key}&Expires={expires}&Signature={signature}"

    def _presign_post(self, key: str) -> PresignedUpload:
        """Generate a minimal presigned POST without boto3 dependency."""

        policy = (
            "{" "\"expiration\":"
            f"\"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() + self.upload_expires))}\""
            ",\"conditions\":["
            f"{{\"bucket\":\"{self.bucket}\"}}"
            ","
            f"[\"starts-with\",\"$key\",\"{key}\"]"
            "]}"
        )
        signature = hmac.new(self.secret_key.encode(), policy.encode(), hashlib.sha256).digest()
        encoded_policy = policy.encode().hex()
        encoded_signature = signature.hex()
        url = f"{self._base_url()}"
        fields = {
            "key": key,
            "AWSAccessKeyId": self.access_key,
            "policy": encoded_policy,
            "signature": encoded_signature,
        }
        return PresignedUpload(url=url, fields=fields, expires_in=self.upload_expires)

    def store_placeholder(self, filename: str, suffix: str) -> S3ObjectDescriptor:
        """Store a placeholder object reference without performing upload."""

        key = self._generate_key(f"{os.path.splitext(filename)[0]}-{suffix}")
        url = f"{self._base_url()}/{quote(key)}"
        logger.debug("Generated placeholder object %s", key)
        return S3ObjectDescriptor(key=key, url=url)
