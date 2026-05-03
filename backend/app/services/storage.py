"""Storage backend abstraction (local filesystem o S3/Cloudflare R2)."""
from __future__ import annotations
import os
from pathlib import Path
from typing import BinaryIO, Optional

from app.core.config import settings


class LocalStorage:
    """Local filesystem storage. Solo para dev y on-prem."""

    def __init__(self, base_path: Path):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def upload(self, key: str, content: bytes | BinaryIO) -> str:
        path = self.base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_bytes(content.read())
        return str(path)

    def download(self, key: str) -> bytes:
        return (self.base / key).read_bytes()

    def get_path(self, key: str) -> str:
        return str(self.base / key)

    def exists(self, key: str) -> bool:
        return (self.base / key).exists()

    def delete(self, key: str) -> None:
        path = self.base / key
        if path.exists():
            path.unlink()


class S3Storage:
    """S3-compatible storage (AWS S3 / Cloudflare R2 / Backblaze B2 / MinIO)."""

    def __init__(self, bucket: str, region: str, endpoint_url: Optional[str] = None,
                 access_key: Optional[str] = None, secret_key: Optional[str] = None):
        import boto3
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key or os.environ.get("S3_ACCESS_KEY"),
            aws_secret_access_key=secret_key or os.environ.get("S3_SECRET_KEY"),
        )

    def upload(self, key: str, content: bytes | BinaryIO) -> str:
        if isinstance(content, bytes):
            self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        else:
            self.client.upload_fileobj(content, self.bucket, key)
        return f"s3://{self.bucket}/{key}"

    def download(self, key: str) -> bytes:
        from io import BytesIO
        buf = BytesIO()
        self.client.download_fileobj(self.bucket, key, buf)
        return buf.getvalue()

    def get_path(self, key: str) -> str:
        """Para S3 devolvemos un path local temporal — descarga al disco."""
        local = Path("/tmp") / "s3_cache" / key
        local.parent.mkdir(parents=True, exist_ok=True)
        if not local.exists():
            self.client.download_file(self.bucket, key, str(local))
        return str(local)

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


def get_storage():
    """Factory que devuelve el backend de storage según config."""
    if settings.storage_backend == "s3":
        return S3Storage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            endpoint_url=os.environ.get("S3_ENDPOINT_URL"),  # para R2: https://<account>.r2.cloudflarestorage.com
        )
    return LocalStorage(settings.storage_local_path)


storage = get_storage()
