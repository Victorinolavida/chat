from typing import BinaryIO

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from flask import current_app

_EXTENSION_KEY = "storage_client"


class StorageError(Exception):
    pass


class StorageService:
    def __init__(self, client, bucket: str, url_ttl: int) -> None:
        self._client = client
        self.bucket = bucket
        self.url_ttl = url_ttl

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self._client.create_bucket(Bucket=self.bucket)
            except ClientError as error:
                raise StorageError(
                    f"could not create bucket {self.bucket!r}"
                ) from error

    def upload(
        self,
        key: str,
        fileobj: BinaryIO,
        content_type: str | None = None,
    ) -> str:
        extra = {"ContentType": content_type} if content_type else {}
        try:
            self._client.upload_fileobj(fileobj, self.bucket, key, ExtraArgs=extra)
        except ClientError as error:
            raise StorageError(f"could not upload {key!r}") from error
        return key

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            raise StorageError(f"could not delete {key!r}") from error

    def presigned_url(self, key: str, ttl: int | None = None) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=ttl or self.url_ttl,
            )
        except ClientError as error:
            raise StorageError(f"could not sign url for {key!r}") from error

    def presigned_upload(
        self,
        key: str,
        content_type: str | None = None,
        max_bytes: int | None = None,
        ttl: int | None = None,
    ) -> dict:
        fields = {}
        conditions = [{"key": key}]
        if content_type:
            fields["Content-Type"] = content_type
            conditions.append({"Content-Type": content_type})
        if max_bytes:
            conditions.append(["content-length-range", 1, max_bytes])
        try:
            return self._client.generate_presigned_post(
                Bucket=self.bucket,
                Key=key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=ttl or self.url_ttl,
            )
        except ClientError as error:
            raise StorageError(f"could not sign upload url for {key!r}") from error


def _client() -> "boto3.client":
    client = current_app.extensions.get(_EXTENSION_KEY)
    if client is None:
        config = current_app.config
        client = boto3.client(
            "s3",
            endpoint_url=config["STORAGE_ENDPOINT"],
            aws_access_key_id=config["STORAGE_ACCESS_KEY"],
            aws_secret_access_key=config["STORAGE_SECRET_KEY"],
            region_name=config["STORAGE_REGION"],
            config=BotoConfig(s3={"addressing_style": "path"}),
        )
        current_app.extensions[_EXTENSION_KEY] = client
    return client


def build_storage_service() -> StorageService:
    config = current_app.config
    return StorageService(
        client=_client(),
        bucket=config["STORAGE_BUCKET"],
        url_ttl=config["STORAGE_URL_TTL"],
    )
