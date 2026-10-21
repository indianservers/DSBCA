import re
from pathlib import Path
from typing import Protocol
from fastapi import HTTPException
from app.core.config import settings


def safe_key(key):
    if (
        not re.fullmatch(r"[a-zA-Z0-9/_\-.]+", key)
        or ".." in key
        or key.startswith("/")
    ):
        raise ValueError("Invalid object key")
    return key


class PrivateStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str, limit: int) -> bytes: ...
    def presign_upload(self, key: str, size: int, sha256: str) -> dict: ...


class LocalPrivateStorage:
    def __init__(self):
        if settings().app_env == "production":
            raise HTTPException(503, "Local storage is forbidden in production")
        self.root = Path(settings().pdf_local_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key):
        path = (self.root / safe_key(key)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Object path escapes private root")
        return path

    def put(self, key, data, content_type):
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError("Immutable object already exists")
            return
        with path.open("xb") as stream:
            stream.write(data)

    def get(self, key, limit):
        path = self.path(key)
        if not path.exists():
            raise FileNotFoundError("Private object not found")
        if path.stat().st_size > limit:
            raise ValueError("Object exceeds processing limit")
        return path.read_bytes()

    def presign_upload(self, key, size, sha256):
        raise HTTPException(
            503,
            "Direct uploads require private S3-compatible storage. Local development supports bounded multipart uploads.",
        )


class S3PrivateStorage:
    def __init__(self):
        import boto3
        from botocore.config import Config

        cfg = settings()
        if (
            not cfg.s3_bucket
            or not cfg.aws_access_key_id
            or not cfg.aws_secret_access_key
        ):
            raise HTTPException(503, "Private object storage is not configured")
        self.bucket = cfg.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=cfg.s3_endpoint_url or None,
            region_name=cfg.s3_region,
            aws_access_key_id=cfg.aws_access_key_id,
            aws_secret_access_key=cfg.aws_secret_access_key,
            config=Config(
                connect_timeout=8,
                read_timeout=30,
                retries={"max_attempts": 2},
                signature_version="s3v4",
            ),
        )

    def put(self, key, data, content_type):
        self.client.put_object(
            Bucket=self.bucket,
            Key=safe_key(key),
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
            IfNoneMatch="*",
        )

    def get(self, key, limit):
        result = self.client.get_object(Bucket=self.bucket, Key=safe_key(key))
        with result["Body"] as stream:
            if result["ContentLength"] > limit:
                raise ValueError("Object exceeds processing limit")
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Object exceeds processing limit")
        return data

    def presign_upload(self, key, size, sha256):
        # POST policy enforces size, content type and exact immutable version key; worker verifies actual hash.
        return self.client.generate_presigned_post(
            self.bucket,
            safe_key(key),
            Fields={
                "Content-Type": "application/pdf",
                "x-amz-server-side-encryption": "AES256",
            },
            Conditions=[
                ["content-length-range", size, size],
                {"Content-Type": "application/pdf"},
                {"x-amz-server-side-encryption": "AES256"},
            ],
            ExpiresIn=180,
        )

    def download_url(self, key, content_type="application/pdf"):
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": safe_key(key),
                "ResponseContentDisposition": "inline",
                "ResponseContentType": content_type,
            },
            ExpiresIn=60,
        )


def storage():
    kind = settings().pdf_storage_backend
    if kind == "local":
        return LocalPrivateStorage()
    if kind == "s3":
        return S3PrivateStorage()
    raise HTTPException(503, "Private PDF storage is not configured")
